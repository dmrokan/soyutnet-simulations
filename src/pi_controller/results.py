import sys
import getopt
import json
from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np


def load_result(fn):
    result_obj = None
    with open(fn, "r") as fh:
        result_obj = json.load(fh)

    result_vs_controller = OrderedDict()

    for trial in result_obj["trials"]:
        if "params" not in trial:
            continue
        params = trial["params"]
        controller_type = params["controller_type"]
        if controller_type not in result_vs_controller:
            result_vs_controller[controller_type] = []
        stats = trial["stats"]
        result_vs_place = []
        for name in stats:
            started_at = stats[name]["started_at"]
            last_at = stats[name]["last_at"]
            count = stats[name]["count"]
            result_vs_place += [last_at - started_at, count]

        var = params["rng"][-1]
        rate = params["produce_rate"]
        result_vs_controller[controller_type].append((rate,) + tuple(result_vs_place))

    for name in result_vs_controller:
        result_vs_controller[name] = np.array(result_vs_controller[name])

    return result_vs_controller


def plot_results(results, output_file=""):
    fig, axes = plt.subplots(2, 1)
    for name in results:
        x = results[name][:, :1]
        tmp = np.array(results[name][:, 2::2])
        y = np.abs(tmp[:, 0] - tmp[:, 1])
        (line,) = axes[0].plot(x, y)
        line.set_label(name)
        y = np.sum(tmp, axis=1)
        (line,) = axes[1].plot(x, y)
        line.set_label(name)

    for ax in axes:
        ax.legend()
        ax.grid()

    axes[0].set(ylabel="Consumer difference")
    axes[1].set(ylabel="Total consumed")
    axes[1].set(xlabel="Producer rate (tokens/sec)")

    plt.show()

    if output_file:
        fig.savefig(output_file)


def main(argv):
    INPUT_FILE = ""
    OUTPUT_FILE = ""
    opts, args = getopt.getopt(argv[1:], "i:o:")
    for o, a in opts:
        if o == "-i":
            INPUT_FILE = a
        elif o == "-o":
            OUTPUT_FILE = a

    if not INPUT_FILE:
        raise RuntimeError("Provide input file: -i <input file name>")

    results = load_result(INPUT_FILE)
    plot_results(results, OUTPUT_FILE)

    return 0


if __name__ == "__main__":
    main(sys.argv)
