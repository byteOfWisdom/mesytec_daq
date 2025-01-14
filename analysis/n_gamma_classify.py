import numpy as np
from sys import argv

def gaussian(x, mu, sigma_sq):
    a = np.sqrt(2 * np.pi * sigma_sq) ** (-1)
    return a * np.exp(- ((x - mu) ** 2) / (2 * sigma_sq))


if __name__ == "__main__":
    mu_a, sigma_a, mu_b, sigma_b = map(float, argv[1:])
    gamma_chance = lambda x: gaussian(x, mu_a, sigma_a)
    neutron_chance = lambda x: gaussian(x, mu_b, sigma_b)

    while True:
        data = list(map(int, input().split(",")))
        short = data[0]
        long = data[1]
        channel = data[2]
        timestamp = data[2]

        if channel != 1:
            continue

        y = (long - short) / long

        probability = neutron_chance(y) / gamma_chance(y)

        print(f"{short}, {long}, {timestamp}, {channel}, {probability}")
