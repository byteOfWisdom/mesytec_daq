# %%
import numpy as np
from matplotlib import pyplot as plt
from scipy import optimize as opt
from scipy import signal as sig


# %%
runs = ["n_gamma_default_settings.csv", "n_y_run_1.csv", "n_y_run_2.csv", "n_y_run_3.csv", "n_y_run_4.csv", "n_y_run_5.csv", "n_y_run_6.csv"]

prefix = "../../calibration_data/scint_test_data/"

def find_range(y, bins, cutoff):
    current_range = [min(y), max(y)]
    h, _ = np.histogram(y, bins, range=current_range)

    while h[0] < cutoff * max(h):
        bin_dist = (current_range[1] - current_range[0]) / bins
        current_range[0] += 0.5 * bin_dist
        h, _ = np.histogram(y, bins, range=current_range)

    while h[-1] < cutoff * max(h):
        bin_dist = (current_range[1] - current_range[0]) / bins
        current_range[1] -= 0.5 * bin_dist
        h, _ = np.histogram(y, bins, range=current_range)

    return current_range


def gaussian(x, a, mu, sigma_sq):
    return a * np.exp(- ((x - mu) ** 2) / (2 * sigma_sq))


def double_gaussian(x, a_1, a_2, mu_1, mu_2, sigma_sq_1, sigma_sq_2):
    return gaussian(x, a_1, mu_1, sigma_sq_1) + gaussian(x, a_2, mu_2, sigma_sq_2)


# %%
def analyze_run(n):
    data = np.transpose(np.loadtxt(prefix + runs[n], delimiter=','))
    long = data[0][data[3] == 1]
    short = data[1][data[3] == 1]

    valid = short < long
    long = long[valid]
    short = short[valid]
    y = (long - short) / long

    autorange = find_range(y, 100, 0.005)
    counts, bins = np.histogram(y, bins=100, range=autorange)
    bin_centers = bins[0:-1] + 0.5 * (bins[1] - bins[0])


    peaks = sig.argrelmax(counts)[0]

    biggest, second = 0, 0

    for peak in peaks:
        if counts[peak] > counts[biggest]:
            biggest = peak

    for peak in peaks:
        if counts[peak] > counts[second] and np.abs(peak - biggest) > 20:
            second = peak

    peak_two = bin_centers[biggest]
    peak_one = bin_centers[second]

    sigma_guess_one = 1.7e-2
    sigma_guess_two = 1.7e-2

    amp_one = counts[second]
    amp_two = counts[biggest]

    params, covariance = opt.curve_fit(
        double_gaussian, bin_centers, counts,
        p0=[amp_one, amp_two, peak_one, peak_two, sigma_guess_one, sigma_guess_two],
        maxfev=99999
    )

    errors = np.sqrt(np.diag(covariance))

    sigma_gamma = np.sqrt(params[4])
    sigma_neutron = np.sqrt(params[5])
    peak_diff = np.abs(params[3] - params[2])

    print(f"sigma_gamma = {sigma_gamma} +- {errors[4]}")
    print(f"sigma_neutron = {sigma_neutron} +- {errors[5]}")
    print(f"mu_gamma = {params[2]} +- {errors[2]}")
    print(f"mu_neutron = {params[3]} +- {errors[3]}")
    print(f"a_gamma = {params[0]} +- {errors[0]}")
    print(f"a_neutron = {params[1]} +- {errors[1]}")


    fom = peak_diff / (2.355 * (sigma_gamma + sigma_neutron))
    print("FOM = ", fom)

    plt.stairs(counts, bins)
    x_values = np.linspace(bins[0], bins[-1], 1000)
    plt.plot(x_values, double_gaussian(x_values, *params))
    plt.title(f"run {n}")
    plt.ylabel("count")
    plt.xlabel(r"$\frac{long - short}{long}$")
    plt.show()
    #plt.savefig(f"run{n}.pdf")
    #plt.cla()

# %%
analyze_run(0)
analyze_run(1)
analyze_run(2)
analyze_run(3)
analyze_run(4)
analyze_run(5)
analyze_run(6)
