#include <cstdint>
#include <cstdio>
#include <stdio.h>
#include <sstream>
#include <string>
#include <sys/types.h>
#include <vector>

using namespace std;

vector<string> split(string& s, char delimiter) {
	stringstream s_stream(s);
	auto res = vector<string>();


	for (auto chunkbuff = string(); getline(s_stream, chunkbuff, delimiter);) {
		res.push_back(chunkbuff);
	}
	return res;
}


const int TIME_COL = 2;

uint64_t parse(string& line) {
	auto values = split(line, ',');
	return stoull(values[TIME_COL]);
}


int main(int argc, char** argv) {
	double pps = argc > 1? atof(argv[1]): 5.0;
	const double time_unit = 12.5; // how many nanoseconds make up 1 count in timestamp

	uint64_t time_lim = (uint64_t) ((1e9 / time_unit) / pps); //timeunits per second / prints per second
	uint count = 0;
	uint64_t last_emitted = 0;
	uint64_t timestamp, l, s;
	uint dump;
	int channel = 0;
	//uint count_goal = 1000;
	auto f = stdin;

	for(;;) {
		if (fscanf(f, "%llu, %llu, %llu, %u, %u\n", &l, &s, &timestamp, &channel, &dump) != 5) return 1;
		++ count;

		if (timestamp - last_emitted > time_lim) {
			printf("%f\n", 1e9 * (double) count / (double) (timestamp - last_emitted));
			fflush(stdout);
			last_emitted = timestamp;

			count = 0;
		}
	}
	return 0;
}
