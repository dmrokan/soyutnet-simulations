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
import statistics
import operator


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

    moments = []

    for trial in data["trials"]:
        if "production_time" not in trial:
            continue
        controller_stats = trial["controller_stats"]
        if controller_stats["weak"] == 1 or controller_stats["eps"] > 1e-2:
            continue
        pt = trial["production_time"]
        dist1 = trial["params"]["PRODUCER1_DELAY"]
        dist2 = trial["params"]["PRODUCER2_DELAY"]
        dt = list(map(operator.sub, pt[1:], pt[:-1]))
        if len(dt) < 2:
            continue

        mu0 = joint_mean(dist1, dist2)
        mu = statistics.mean(dt)
        std0 = joint_variance(dist1, dist2) ** 0.5
        std = statistics.variance(dt) ** 0.5
        res = [mu, mu0, std, std0]
        moments.append(res)

    data["moments"] = moments

    return data


def main(argv):
    results = load_results()
    output_file = open(DIR + "/results.txt", "w")
    rest_suffix = ".."
    line_suffix = " " * len(rest_suffix)
    _table = partial(print, file=output_file)
    _print = lambda *args: print(line_suffix, *args, end="", file=output_file)
    _print_line = lambda *args: print(line_suffix, *args, file=output_file)
    _print_directive = lambda *args: print(rest_suffix, *args, file=output_file)
    tab = "\t\t"
    column_width = 8
    sep = "=" * (column_width - 1)

    def print_separator(n):
        {_print(f"{sep:<{column_width}}") for i in range(n)}
        _print_line()

    def start_table(table_index):
        _table(f"table-{table_index}-start")
        _print_directive(f"_table_{table_index}:" + os.linesep)
        _print_directive(f"table:: **Table {table_index}:** |table_{table_index}|")
        _print_line(":width: 100%" + os.linesep)

    def end_table(table_index):
        _table(f"table-{table_index}-end")

    start_table(1)

    tags = ["mu", "mu0", "std", "std0"]
    print_separator(len(tags))
    {_print(f"{val:<{column_width}}") for val in tags}
    _print_line()
    print_separator(len(tags))

    for stat in results["moments"]:
        {_print(f"{int(val):<{column_width}}") for val in stat}
        _print_line()
    print_separator(len(tags))

    end_table(1)

    start_table(2)

    i = 0
    prev_bw = 0
    for trial in results["trials"]:
        if "controller_stats" not in trial:
            continue
        controller_stats = trial["controller_stats"]
        bw = controller_stats["bw"]
        del controller_stats["bw"]
        if 8 == bw != prev_bw:
            print_separator(len(controller_stats) + 2)
            end_table(2)
            start_table(3)
            i = 0
        params = trial["params"]
        dt = int(params["PRODUCER1_DELAY"][0] - params["PRODUCER2_DELAY"][0])
        real_slow = int(dt > 0) + 1
        dt = abs(dt)
        slow = controller_stats["slow"]
        if slow != real_slow:
            slow = f"{slow}*"
        controller_stats["slow"] = slow
        controller_stats["Dt0"] = dt
        dt_hat = controller_stats["Dt"]
        controller_stats["err"] = round(abs((dt_hat - dt) / (dt_hat + 1e-2)), 2)
        if i == 0:
            print_separator(len(controller_stats))
            {_print(f"{key:<{column_width}}") for key in controller_stats}
            _print_line()
            print_separator(len(controller_stats))
        {_print(f"{value:<{column_width}}") for value in controller_stats.values()}
        _print_line()
        i += 1
        prev_bw = bw

    print_separator(len(controller_stats))
    end_table(3)

    return 0


if __name__ == "__main__":
    main(sys.argv)
