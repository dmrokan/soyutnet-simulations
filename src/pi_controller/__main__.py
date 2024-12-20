# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
import sys
from itertools import product

from .main import main, USAGE
from .results import main as show_results
from ..common.clean import clean

DIR = os.path.dirname(os.path.realpath(__file__))
TIME = 2.0
MEAN = 0.01
RNG_PARAMS = f"exponential,{MEAN}"
K_PIS = ["1e-2,1e-4", "1e-2,0"]
CONT = ["none", "C1", "C2"]
PRODUCE_RATE_SCALER = 25
END = 30


def _results(argv):
    for i in range(1, len(K_PIS) + 1):
        log_file = f"{DIR}/results_{i}.json"
        output_file = f"{DIR}/result_{i}.png"
        args = ["", "-i", log_file, "-o", output_file]
        if show_results(args + argv[1:]) != 0:
            break

    return 0


def _main(argv):
    argv = ["-T", TIME] + argv[1:]

    i = 1
    for k in K_PIS:
        log_file = f"{DIR}/results_{i}.json"
        with open(log_file, "w") as fh:
            fh.write('{ "trials": [' + os.linesep)

        for c, j in product(CONT, range(1, END + 1)):
            args = [
                "",
                "-c",
                c,
                "-r",
                RNG_PARAMS,
                "-o",
                log_file,
                "-p",
                PRODUCE_RATE_SCALER * j,
                "-K",
                k,
            ]
            args += argv
            print("Starting simulation with arguments:")
            print("  ", args)
            main(args)
            with open(log_file, "a") as fh:
                fh.write(f",{os.linesep}")

        with open(log_file, "a") as fh:
            fh.write("{}]}" + os.linesep)
        i += 1

    return 0


a1 = ""
if len(sys.argv) > 1:
    a1 = sys.argv[1]

if "-h" in sys.argv:
    USAGE()
    sys.exit(0)

match a1:
    case "results":
        sys.exit(_results(sys.argv[1:]))
    case "main":
        sys.exit(_main(sys.argv[1:]))
    case "graph":
        sys.exit(main(["", "-o", DIR + "/graph.gv", "-G"]))
    case "clean":
        sys.exit(clean(DIR))
    case _:
        sys.exit(_main(["main"] + sys.argv[1:]))
