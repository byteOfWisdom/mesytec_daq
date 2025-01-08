#include "mesytec-mvlc/mvlc.h"
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
FILE* out_file;

void interrupt(int s) {
	(void) s;
	running = false;
	auto ec = mvlc.disconnect();
	if (ec) {
		std::cout << "ERROR: " << ec << std::endl;
	}
	std::fclose(out_file);
	// TODO: find non-segfaulting way of exiting
	exit(0);
}

struct qdc_data {
	uint8_t channel;
	uint16_t long_integration;
	uint16_t short_integration;
	uint64_t time_diff;

	bool operator==(qdc_data& other) {
		return (other.channel == this->channel)
		&& (other.long_integration == this->long_integration)
		&& (other.short_integration == this->short_integration)
		&& (other.time_diff == this->time_diff);
	};
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

	qdc_data res = {};
	res.time_diff = 0;

	const uint32_t header_mask = 0b1111 << 28;//0xf0000000;
	const uint32_t data_mask = 0x0000ffff;

	const uint32_t event_data_header = 0b0001 << 28;
	const uint32_t timing_header = 0b11 << 30;
	const uint32_t extended_timing_header = 0b0010 << 28;
	const uint32_t meta_header = 0b0100 << 28;

	const uint32_t time_mask = ~timing_header;

	for (uint8_t i = 0; i < data.data.size; ++i) {
		if ((raw[i] & header_mask) == event_data_header) {
			auto [chan, value] = parse_event(raw[i]);
			if (chan <= 15) res.channel = chan;
			if (chan <= 15) res.long_integration = value;
			if (chan >= 48 && chan <= 63) res.short_integration = value;
		} else if ((raw[i] & timing_header) == timing_header) {
			res.time_diff |= (raw[i] & time_mask);
			//printf("got normal time stamp: %u\n", raw[i] & time_mask);
		} else if ((raw[i] & header_mask) == extended_timing_header) {
			res.time_diff |= ((uint64_t) (raw[i] & data_mask)) << 30;
			//printf("got extended time stamp: %u\n", raw[i] & data_mask);
		} else if ((raw[i] & header_mask) == meta_header) {
			//uint16_t wc = 0b1111111111 & raw[i];
			//printf("got wc: %u while size is: %u\n", wc, data.data.size);
			continue;
		}
	}

	if (res.time_diff == 0) {
		std::cout << "got event without timestamp\n";
		for (uint8_t i = 0; i < data.data.size; ++i) {
			std::cout << std::bitset<32>(raw[i]) << "\n";
		}
	}

	return res;
}


int main(int argc, char* argv[]){
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

	ListfileParams listfileParams = {.writeListfile = false};

	out_file = std::fopen(argv[2], "w");

	readout_parser::ReadoutParserCallbacks parserCallbacks;
	parserCallbacks.eventData = [] (
		void *, int crateId, int eventIndex, const readout_parser::ModuleData *moduleDataList, unsigned moduleCount)
	{
		(void) moduleCount;
		(void) crateId;
		(void) eventIndex;
		qdc_data data = parse_event_data(moduleDataList[0]);
		std::fprintf(out_file, "%i, %i, %lli, %i, %lli\n",
			data.long_integration, data.short_integration, data.time_diff, data.channel, (uint64_t) 0
		);
		fflush(out_file);
	};

	bool print_sys_event = false;

	parserCallbacks.systemEvent = [=] (void *, int crateId, const u32 *header, u32 size) {
		if (!print_sys_event) return;
		std::cout
			<< "SystemEvent: type=" << system_event_type_to_string(
				system_event::extract_subtype(*header))
			<< ", size=" << size << ", bytes=" << (size * sizeof(u32))
			<< std::endl;
		fmt::print("system event: crateId={}, header={:08x} \n", crateId, *header);
	};

	auto rdo = make_mvlc_readout(
		mvlc,
	 	crateConfig,
	 	listfileParams,
		parserCallbacks
	);


	std::cout << "starting readout" << std::endl;
	signal (SIGINT, &interrupt);

	if (auto ec = rdo.start()) {
		std::cerr << "Error starting readout: " << ec.message() << std::endl;
		throw std::runtime_error("ReadoutWorker error");
	}

	while (!rdo.finished());

	interrupt(0);

	return 0;
}
