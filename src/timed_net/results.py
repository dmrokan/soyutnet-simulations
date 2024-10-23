# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
import sys
import getopt
import json
import glob
from pathlib import Path
import math
from collections import OrderedDict
from functools import partial

import numpy as np
import matplotlib.pyplot as plt


DIR = os.path.dirname(os.path.realpath(__file__))


# [[normal-dist-func-defs-start]]


def pdf(x, mean=0, std=1):
    """phi"""
    var = std**2
    a = 2 * math.pi * var
    a = 1 / (a**0.5)
    return a * math.exp(-((x - mean) ** 2) / (2 * var))


def cdf(x, mean=0, std=1):
    """Phi"""
    a = 2**0.5
    return 0.5 * (1 + math.erf((x - mean) / (std * a)))


# [[normal-dist-func-defs-end]]


def joint_mean(dist1, dist2):
    mu1, std1 = dist1
    mu2, std2 = dist2
    var1 = std1**2
    var2 = std2**2
    theta = (var1 + var2) ** 0.5
    a = (mu1 - mu2) / theta
    return mu1 * cdf(a) + mu2 * cdf(-a) + theta * pdf(a)


def joint_variance(dist1, dist2):
    mu1, std1 = dist1
    mu2, std2 = dist2
    var1 = std1**2
    var2 = std2**2
    theta = (var1 + var2) ** 0.5
    a = (mu1 - mu2) / theta
    jmu = joint_mean(dist1, dist2)
    return (
        (var1 + mu1**2) * cdf(a)
        + (var2 + mu2**2) * cdf(-a)
        + (mu1 + mu2) * theta * pdf(a)
        - jmu**2
    )


def load_results():
    data = None
    with open(DIR + "/results.json") as fh:
        data = json.load(fh)

    if data is None:
        raise RuntimeError("Could not load results")

    results = []

    for trial in data["trials"]:
        if "production_time" not in trial:
            continue
        pt = np.array(trial["production_time"], dtype=np.float64)
        dist1 = trial["params"]["PRODUCER1_DELAY"]
        dist2 = trial["params"]["PRODUCER2_DELAY"]

        mu = joint_mean(dist1, dist2)
        std = joint_variance(dist1, dist2) ** 0.5
        res = [mu, std]
        dt = pt[1:] - pt[:-1]
        res.append(np.mean(dt).item(0))
        res.append(np.var(dt).item(0) ** 0.5)
        results.append(res)

    return results


def main(argv):
    results = load_results()
    output_file = open(DIR + "/results.txt", "w")
    _print = partial(print, end="", file=output_file)
    _print_line = partial(print, file=output_file)
    tab = "\t\t"

    tags = ["mu0", "std0", "mu", "std"]
    {_print(f"{val:>8}") for val in tags}
    _print_line(os.linesep)

    for res in results:
        {_print(f"{int(val):>8}") for val in res}
        _print_line()

    return 0


if __name__ == "__main__":
    main(sys.argv)
