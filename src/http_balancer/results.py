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
        if (ab_concurrency // 8) % 4 != 0:
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


def plot_results(results):
    fig0, ax0 = plt.subplots(1, 1)

    fig, axes = plt.subplots(len(results[list(results.keys())[0]]), 1)

    for controller_type in results:
        keys = sorted(results[controller_type].keys())
        i = 0
        for ab_concurrency in keys:
            result = results[controller_type][ab_concurrency]
            x = result[:, 1]  # Time in ms
            y = result[:, 0] / 100  # Percentage served
            if i == 1:
                line = ax0.plot(x, y)
                line[0].set_label(controller_type)
                ax0.set_title(f"{ab_concurrency} concurrent requesters")
            y = np.gradient(y, x)
            line = axes[i].plot(x, y)
            line[0].set_label(controller_type)
            axes[i].set(ylabel=f"{ab_concurrency}")
            i += 1

    ax0.legend()
    ax0.grid()
    axes[0].legend()
    for i in range(len(axes)):
        axes[i].grid()

    ax0.set_xlabel("Time (ms)")
    ax0.set_ylabel("Percentage of requests")
    axes[0].set_title("Serving time distrbution")
    axes[-1].set_xlabel("Time (ms)")

    fig.subplots_adjust(hspace=0.4)
    fig.set_size_inches(10, 10)

    plt.show()

    fig0.savefig(DIR + "/result_1.png")
    fig.savefig(DIR + "/result_2.png")


def main(argv):
    results = load_results()
    plot_results(results)

    return 0


if __name__ == "__main__":
    main(sys.argv)
