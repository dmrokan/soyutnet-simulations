# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
import sys
import getopt
import json
import glob
from pathlib import Path
import csv
from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np


DIR = os.path.dirname(os.path.realpath(__file__))


def load_results():
    filenames = sorted(glob.glob(DIR + "/result_*.csv"))

    results = OrderedDict()

    for fn in filenames:
        p = Path(fn)
        parts = p.name.split("_")
        controller_type = parts[1]
        ab_concurrency = int(parts[2])
        if False and (ab_concurrency // 8) % 4 != 0:
            continue

        data = []
        with open(fn, "r") as csvfile:
            rows = csv.reader(csvfile)
            next(rows, None)  # Skip header
            for row in rows:
                data.append(tuple([float(val) for val in row]))

        if controller_type not in results:
            results[controller_type] = {}
        results[controller_type][ab_concurrency] = np.array(data)

    return results


def fit_gaussian(x, pdf):
    dx = x[1:] - x[:-1]
    x = x[1:]
    y = pdf[1:]
    tmp = dx * x * y
    mu = np.sum(tmp)
    x -= mu
    tmp = dx * x * x * y
    var = np.sum(tmp)
    std = np.sqrt(var)
    x += mu
    fx = lambda a, mu, c, x: a * c * np.exp(-0.5 * np.pow(c * (x - mu), 2))
    a = 1.0 / np.sqrt(2 * np.pi)
    c = 1.0 / std
    step = 1e-2 * min(c, mu)
    it = 50000
    dtotal_end = 1e-12
    dtotal = dtotal_end
    while it > 0 and dtotal >= dtotal_end:
        f = fx(a, mu, c, x)
        Y = f - y
        dmu = step * np.sum(Y * f * (c * (x - mu)))
        dc = step * np.sum(Y * (f / c - f * (c * (x - mu))))
        mu -= dmu
        c -= dc
        dtotal = dmu * dmu + dc * dc
        it -= 1

    y = fx(a, mu, c, x)
    return y, mu, 1 / c


def plot_results(results):
    fig0, axes0 = plt.subplots(len(results[list(results.keys())[0]]), 1)
    fig, axes = plt.subplots(len(results[list(results.keys())[0]]), 1)

    for controller_type in results:
        keys = sorted(results[controller_type].keys())
        i = 0
        for ab_concurrency in keys:
            result = results[controller_type][ab_concurrency]
            x = result[:, 1]  # Time in ms
            y = result[:, 0] / 100  # Percentage served
            line = axes0[i].plot(x, y)
            if i == 0:
                line[0].set_label(controller_type)
            y = np.gradient(y, x)
            line = axes[i].plot(x, y)
            if i == 0:
                line[0].set_label(controller_type)
            try:
                yhat, mu, std = fit_gaussian(np.array(x), np.array(y))
                line = axes[i].plot(x[1:], yhat, "-.")
                line[0].set_label(f"$\\mu$:{mu:.02f},$\\sigma$:{std:.02f}")
            except:
                pass
            axes0[i].set(ylabel=f"{ab_concurrency}")
            axes[i].set(ylabel=f"{ab_concurrency}")
            i += 1

    axes0[0].legend()
    for i in range(len(axes)):
        axes0[i].grid()
        axes[i].grid()
        axes[i].legend()

    axes0[0].set_title("Percentage of requests completed within time")
    axes0[-1].set_xlabel("Time (ms)")
    axes[0].set_title("Serving time distrbution")
    axes[-1].set_xlabel("Time (ms)")

    fig.subplots_adjust(hspace=0.4)
    fig.set_size_inches(10, 10)
    fig0.subplots_adjust(hspace=0.4)
    fig0.set_size_inches(10, 10)

    plt.show()

    fig0.savefig(DIR + "/result_1.png")
    fig.savefig(DIR + "/result_2.png")


def main(argv):
    results = load_results()
    plot_results(results)

    return 0


if __name__ == "__main__":
    main(sys.argv)
