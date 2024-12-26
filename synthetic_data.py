from numba import njit, jit
import numpy as np
from sys import argv
from time import sleep


def main():
    count = int(float(argv[1]))
    delta_t = float(argv[2])
    cps = int(float(argv[3]))
    data = make_data_batch(count, neutron_chance=0.5, delta_t=delta_t)
    offset = 0
    while True:
        print_data(data, cps, offset)
        offset += count
        sleep(count / cps)


@njit
def print_data(dataset, counts_per_second, offset):
    delay_s = 1 / counts_per_second
    d_count = len(dataset[0])
    for i in range(d_count):
        csv_line = ", ".join([str(dataset[0][i]), str(dataset[1][i]), str(dataset[2][i] + offset), str(dataset[3][i])])
        print(csv_line)


@njit
def make_data_batch(count: int, neutron_chance: float, delta_t: float):
    channel = np.ones(count, dtype=np.uint8)
    longs = np.ones(count, dtype=np.uint32)
    shorts = np.ones(count, dtype=np.uint32)
    times = np.ones(count, dtype=np.uint32)

    is_neutron = np.random.rand(count) < neutron_chance
    long_seed = np.abs(np.random.normal(0.0, 20000.0, count))
    neutron_seed = np.random.normal(0.0, 0.05, count)
    gamma_seed = np.random.normal(0.0, 0.1, count)

    for i in range(count):
        times[i] = i
        if is_neutron[i]:
            longs[i] = np.uint32(long_seed[i])
            lsl = 0.1 + neutron_seed[i]
            shorts[i] = np.uint32(longs[i] * (1.0 - lsl))
        else:
            longs[i] = np.uint32(long_seed[i])
            lsl = 0.4 + gamma_seed[i]
            shorts[i] = np.uint32(longs[i] * (1.0 - lsl))

    return longs, shorts, times, channel



if __name__ == "__main__":
    main()
