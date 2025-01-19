#!python
import numpy as np
from sys import argv, stdin

def gaussian(x, mu, sigma_sq):
    a = np.sqrt(2 * np.pi * sigma_sq) ** (-1)
    return a * np.exp(- ((x - mu) ** 2) / (2 * sigma_sq))

class ny_classifier:
    def __init__(self, mu, sigma_sq, binary = False):
        self.mu = mu
        self.sigma_sq = sigma_sq

    def __call__(self, long, short):
        y = (long - short) / long

        return
