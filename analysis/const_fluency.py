# %%
from ast import Param
import numpy as np
from scipy import optimize as opt
from scipy import signal as sig
from matplotlib import pyplot as plt
from labtools import perror

"""
when a constant fluency is assumed for the measurement time,
the total neutron count can be apporximated as the area under the curve
for the neutorn gaussian.
"""
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
    return a * np.exp( 0. - ((x - mu) * (x - mu)) / (2 * sigma_sq))

def e_gaussian(x, a, mu, sigma_sq):
    return a / np.exp(((x - mu) ** 2) / (2 * sigma_sq))



def double_gaussian(x, a_1, a_2, mu_1, mu_2, sigma_sq_1, sigma_sq_2):
    return gaussian(x, a_1, mu_1, sigma_sq_1) + gaussian(x, a_2, mu_2, sigma_sq_2)


def fit_gaussians(data):
    bin_count = 90
    long = data[0][data[3] == 1]
    short = data[1][data[3] == 1]

    valid = short < long
    long = long[valid]
    short = short[valid]
    y = (long - short) / long

    autorange = find_range(y, bin_count, 0.005)
    counts, bins = np.histogram(y, bins=bin_count, range=autorange)
    bin_centers = bins[0:-1] + 0.5 * (bins[1] - bins[0])

    index_of_peak, = np.where(counts == np.max(counts[bin_centers > 0.4]))
    peak_two = bin_centers[index_of_peak[0]]
    peak_one = 0.32 #bin_centers[second]

    sigma_guess_one = 1.7e-3
    sigma_guess_two = 1.7e-3

    amp_one = np.max(counts[bin_centers < 0.4])
    amp_two = np.max(counts[bin_centers > 0.4])

    params, covariance = opt.curve_fit(
        double_gaussian, bin_centers, counts,
        p0=[amp_one, amp_two, peak_one, peak_two, sigma_guess_one, sigma_guess_two],
        maxfev=99999
    )

    errors = np.sqrt(np.diag(covariance))

    sigma_gamma = np.sqrt(params[4])
    sigma_neutron = np.sqrt(params[5])
    peak_diff = np.abs(params[3] - params[2])


    fom = peak_diff / (2.355 * (sigma_gamma + sigma_neutron))
    if fom < 1.0:
        print(f"figure of merit for this run is very small! (fom={fom})")

    plot = False
    if plot:
        plt.stairs(counts, bins)
        x_values = np.linspace(bins[0], bins[-1], 1000)
        plt.plot(x_values, double_gaussian(x_values, *params))
        plt.plot(bin_centers[bin_centers > params[2]], gaussian(bin_centers[bin_centers > params[2]], params[1], params[3], params[5]), linestyle="None", marker="x")
        plt.title(f"run")
        plt.ylabel("count")
        plt.xlabel(r"$\frac{long - short}{long}$")
        plt.show()


    return {
        "gamma": {
            "sigma_sq": params[4], "amp": params[0], "mu": params[2],
            "erros": {"sigma_sq": errors[4], "amp": errors[0], "mu": errors[2]}
        },
        "neutron": {
            "sigma_sq": params[5], "amp": params[1], "mu": params[3],
            "erros": {"sigma_sq": errors[5], "amp": errors[1], "mu": errors[3]}
        },
        "bins": bin_centers,
    }


def get_runtime(data):
    overflow_counts = (2 ** 31) - 1 # only when extended timestamp is not used

    timestamps = data[2][data[3] == 1]

    delta_ts = timestamps[1:] - timestamps[:-1]
    delta_ts[delta_ts < 0] += overflow_counts
    return sum(delta_ts)


def count_rate(data):
    #print()
    #print(f"total events: {len(data[0])}")
    time_constant = 6.25e-8 #12.5e-9 #TODO enter correct time constant for the daq (if 12.5ns is wrong)
    delta_t = perror.ev(get_runtime(data) * time_constant, time_constant)
    #print(f"delta t = {delta_t}")
    params = fit_gaussians(data)
    n = params["neutron"]

    mu = perror.ev(n["mu"], n["erros"]["mu"])
    amp = perror.ev(n["amp"], n["erros"]["amp"])
    sigma_sq = perror.ev(n["sigma_sq"], n["erros"]["sigma_sq"])

    counts = sum(gaussian(params["bins"][params["bins"] > params["gamma"]["mu"]], amp, mu, sigma_sq))
    #print(f"counts = {counts}")
    return counts / delta_t


def load(file):
    raw = np.transpose(np.loadtxt(file, delimiter=","))
    return raw

def filename(thickness):
    prefix = "../../calibration_data/scint_test_data/"
    shielding_runs = "shielding_"
    return prefix + shielding_runs + str(thickness) + "mm.csv"
# %%
def alt_count_rate(data, params):
    time_constant = 6.25e-8 #12.5e-9 #TODO enter correct time constant for the daq (if 12.5ns is wrong)
    delta_t = perror.ev(get_runtime(data) * time_constant, time_constant)

    gamma_dist = lambda x: gaussian(
        x, 1.,
        params["gamma"]["mu"],
        params["gamma"]["sigma_sq"]
    )

    neutron_dist = lambda x: gaussian(
        x, 1.,
        params["neutron"]["mu"],
        params["neutron"]["sigma_sq"]
    )


    neutron_counts = 1.
    gamma_counts = 1.

    long = data[0][data[3] == 1]
    short = data[1][data[3] == 1]

    valid = short < long
    long = long[valid]
    short = short[valid]
    events = (long - short) / long

    for event in events:
        relative_count = 0.
        if event > params["gamma"]["mu"] + 3. * np.sqrt(params["gamma"]["sigma_sq"]):
            relative_count = 1.
        neutron_counts += relative_count
        gamma_counts += 1. - relative_count

    #print(f"counts = {counts}")
    return neutron_counts / delta_t


# %%
def classical_analysis():
    runs = [0, 55, 110, 165, 220, 275, 330]
    files = [filename(run) for run in runs]
    count_rates = [count_rate(load(file)) for file in files]

    d = np.array(runs, dtype=np.float64)

    exp_decay = lambda x, a, b: a * np.exp(- b * x)
    params, cov = opt.curve_fit(exp_decay, d, count_rates, p0 = [0.2, 1e-2])
    errors = np.sqrt(np.diag(cov))

    plt.errorbar(runs, perror.value(count_rates), perror.error(count_rates), marker='x', linestyle="None", label="event rate", color="red")
    d_range = np.linspace(0., 350., 1000)
    plt.plot(d_range, exp_decay(d_range, *params), label="e-Fit", color="blue")
    a = perror.ev(params[0], errors[0])
    b = perror.ev(params[1], errors[1])
    print(f"a = {a} s^-1")
    print(f"b = {b} mm^-1")
    plt.title(r"$d_{\frac{1}{2}} = " + str(np.log(2) / b) + r"mm$")
    plt.legend()
    plt.xlabel("PE-shielding [mm]")
    plt.ylabel(r"neutron rate $[s^{-1}]$")
    plt.grid()
    plt.show()


classical_analysis()

# %%
def per_event_judging():
    runs = [0, 55, 110, 165, 220, 275, 330]
    files = [filename(run) for run in runs]

    calibration_file = "../../calibration_data/scint_test_data/n_gamma_default_settings.csv"
    cal_params = fit_gaussians(load(calibration_file))

    count_rates = [alt_count_rate(load(file), cal_params) for file in files]
    print(count_rates)

    d = np.array(runs, dtype=np.float64)

    exp_decay = lambda x, a, b: a * np.exp(- b * x)
    params, cov = opt.curve_fit(exp_decay, d, count_rates, p0 = [count_rates[0].value, 1e-2])
    errors = np.sqrt(np.diag(cov))

    plt.errorbar(runs, perror.value(count_rates), perror.error(count_rates), marker='x', linestyle="None", label="event rate", color="red")
    d_range = np.linspace(0., 350., 1000)
    plt.plot(d_range, exp_decay(d_range, *params), label="e-Fit", color="blue")
    a = perror.ev(params[0], errors[0])
    b = perror.ev(params[1], errors[1])
    print(f"a = {a} s^-1")
    print(f"b = {b} mm^-1")
    plt.title(r"$d_{\frac{1}{2}} = " + str(np.log(2) / b) + r"mm$")
    plt.legend()
    plt.xlabel("PE-shielding [mm]")
    plt.ylabel(r"neutron rate $[s^{-1}]$")
    plt.grid()
    plt.show()

per_event_judging()


# %%
def dist_analysis():
    dist_name = lambda x: f"../../calibration_data/scint_test_data/fluency_{str(x)}cm.csv"
    runs = [40, 60, 80, 100]
    files = [dist_name(dist) for dist in runs]
    count_rates = [count_rate(load(file)) for file in files]

    d = np.array(runs, dtype=np.float64)

    lin = lambda x, a, b: a * x + b
    x_vals = 1 / (d ** 2)
    params, cov = opt.curve_fit(lin, x_vals, count_rates)
    errors = np.sqrt(np.diag(cov))

    d_range = 1 / (np.linspace(38., 120., 1000) ** 2)
    plt.plot(d_range, lin(d_range, *params), label=r"$ax + b$", color="blue")
    plt.errorbar(x_vals, perror.value(count_rates), perror.error(count_rates), marker='x', linestyle="None", label="event rate", color="red")
    a = perror.ev(params[0], errors[0])
    b = perror.ev(params[1], errors[1])
    print(f"a = {a} cm^2/s")
    print(f"b = {b} 1/s")
    plt.title(r"count rate and distance")
    plt.legend()
    plt.xlabel(r"Inverse square distance $[\frac{1}{cm^2}]$")
    plt.ylabel(r"neutron rate $[s^{-1}]$")
    plt.grid()
    plt.show()

dist_analysis()
