#include "mesytec-mvlc/mvlc.h"
#include "mesytec-mvlc/mvlc_blocking_data_api.h"
#include "mesytec-mvlc/mvlc_factory.h"
#include <bitset>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <mesytec-mvlc/mesytec-mvlc.h>
#include <sys/signal.h>
#include <sys/types.h>
#include <tuple>
#include <signal.h>
#include <stdio.h>

using namespace mesytec::mvlc;

bool running = true;

MVLC mvlc;
FILE* test;

void interrupt(int s) {
	running = false;
	auto ec = mvlc.disconnect();
	if (ec) {
		std::cout << "ERROR: " << ec << std::endl;
	}
	std::fclose(test);
	exit(0);
}

struct qdc_data {
	uint8_t channel;
	uint16_t long_integration;
	uint16_t short_integration;
	uint16_t time_diff;
	uint16_t trigger_time_diff;
};


void print_qdc_event(qdc_data event) {
	std::printf("got an event on channel: %d\n", event.channel);
	std::printf("long: %i, short: %i\n", event.long_integration, event.short_integration);
}


std::tuple<uint8_t, uint16_t> parse_event(uint32_t data_block) {
	std::bitset<32> bin_data(data_block);

	const uint32_t channel_mask = 0x00ff0000;
	const uint32_t value_mask = 0x0000ffff;

	uint8_t id = (uint8_t) ((data_block & channel_mask)  >> 16);
	uint16_t data = (uint16_t) (data_block & value_mask);
	return {id, data};
}


qdc_data parse_event_data(readout_parser::ModuleData data) {
	uint32_t* raw = (uint32_t*) data.data.data;

	/*
	if (data.data.size != (uint16_t) (raw[0] & 0x000000ff)) {
		std::printf("received \n");
		return {42, 0, 0, 0, 0};
		} */

	qdc_data res = {};

	for (uint8_t i = 1; i <= 3; ++i) {
		auto [chan, value] = parse_event(raw[i]);
		if (chan <= 15) res.channel = chan;
		if (chan <= 15) res.long_integration = value;
		if (chan >= 48 && chan <= 63) res.short_integration = value;
		if (chan >= 16 && chan <= 31) res.time_diff = value;
	}

	return res;
}


int main(int argc, char* argv[]){
	// MVLC connection overrides
	std::string opt_mvlcEthHost;
	std::string opt_mvlcUSBSerial;

	// listfile and run options
	bool opt_noListfile = true;
	bool opt_overwriteListfile = false;
	std::string opt_listfileOut;
	std::string opt_listfileCompressionType = "lz4";
	int opt_listfileCompressionLevel = 0;
	std::string opt_crateConfig;

	if (argc < 3) {
		std::cout << "to few args given. aborting!" << std::endl;
	 	return 1;
	}

	std::ifstream inConfig(argv[1]);
	CrateConfig crateConfig = {};
	try {
		crateConfig = crate_config_from_yaml(inConfig);
	}
	catch (const std::runtime_error &e) {
		std::cerr << "Error parsing CrateConfig: " << e.what() << std::endl;
		return 1;
	}


	std::cout << "Using mesytec-mvlc library version " << library_version() << std::endl;

	mvlc = make_mvlc(crateConfig);
	mvlc.setDisableTriggersOnConnect(true);

	if (auto ec = mvlc.connect())
	{
		std::cout << "Could not connect to mvlc: " << ec.message() << std::endl;
		return 1;
	}

	std::cout << "Connected to MVLC, " << mvlc.connectionInfo() << std::endl;

	ListfileParams listfileParams = {
		.writeListfile = !opt_noListfile,
		.filepath = opt_listfileOut,
		.overwrite = opt_overwriteListfile,

		.compression = (opt_listfileCompressionType == "lz4"
		? ListfileParams::Compression::LZ4
		: ListfileParams::Compression::ZIP),

		.compressionLevel = opt_listfileCompressionLevel,
	};

	readout_parser::ReadoutParserCallbacks parserCallbacks;

	test = std::fopen(argv[2], "w");

	auto rdo = make_mvlc_readout_blocking(
		mvlc,
	 	crateConfig,
	 	listfileParams
	);

	std::cout << "starting readout" << std::endl;

	if (auto ec = rdo.start())
	{
		std::cerr << "Error starting readout: " << ec.message() << std::endl;
		throw std::runtime_error("ReadoutWorker error");
	}

	signal (SIGINT, &interrupt);

	uint64_t event_goal = argc > 3? (uint64_t) atof(argv[3]) : 0;
	uint64_t events_gotten = 0;

	if (event_goal != 0) {
		printf("fetching %lli events\n", event_goal);
	}

	while (running && (event_goal == 0 || events_gotten <= event_goal)) {
		auto event = next_event(rdo);
		if (event.type == EventContainer::Type::Readout) {
			++ events_gotten;
			//printf("logged %lli events\n", events_gotten);
			qdc_data data = parse_event_data(event.readout.moduleDataList[0]);
			std::fprintf(test, "%i, %i, %i, %lli\n", data.long_integration, data.short_integration, data.time_diff, events_gotten);
			fflush(test);
		}
	}

	interrupt(0);

	return 0;
}
