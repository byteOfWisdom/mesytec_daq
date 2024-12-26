#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <time.h>
#include <tuple>
#include <random>

std::random_device rd;
std::mt19937_64 gen(rd());
std::normal_distribution<double> neutron_dist(0.1, 0.1);
std::normal_distribution<double> gamma_dist(0.4, 0.2);
std::normal_distribution<double> long_dist(0.0, 0.5);
std::uniform_int_distribution<uint16_t> part_kind;


std::tuple<uint64_t, uint64_t> make_event(double lsl, double max_energy) {
	double long_int = pow(std::abs(long_dist(gen)), 1.3) * max_energy;
	double short_int = long_int * (1. - lsl);
	return std::make_tuple(std::round(long_int), std::round(short_int));
}


std::tuple<uint64_t, uint64_t> make_neutron() {
	double lsl = neutron_dist(gen);
	return make_event(lsl, 3e5);
}

std::tuple<uint64_t, uint64_t> make_gamma() {
	double lsl = gamma_dist(gen);
	return make_event(lsl, 2e5);
}


int main(int argc, char** argv) {
	uint32_t events_per_second = argc > 1? (uint32_t) atof(argv[1]): 100;
	double jitter = argc > 2? atof(argv[2]): 0.;

	uint64_t timestamp = 0;
	uint8_t channel = 1;
	uint16_t neutron_chance = 50;
	uint32_t loop_ns = events_per_second == 1? 1e9 -1: 1e9 / events_per_second;
	std::normal_distribution<double> timing_jitter((double) loop_ns, (double) loop_ns * jitter);

	timespec loop_time = {.tv_sec=0, .tv_nsec=loop_ns};

	while (1) {
		auto particle_kind = part_kind(gen) % 100 > neutron_chance;
		auto [long_value, short_value] = particle_kind ? make_neutron(): make_gamma();
		printf("%lli, %lli, %lli, %i\n", long_value, short_value, timestamp / 12, channel);
		fflush(stdout);
		if (jitter > 0) {
			loop_ns = (uint32_t) timing_jitter(gen);
			loop_time.tv_nsec = loop_ns;
		}

		timestamp += loop_ns;
		nanosleep(&loop_time, NULL);
	}
	return 0;
}
