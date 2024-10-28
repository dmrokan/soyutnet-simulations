# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
import sys
import shutil
import subprocess
import random
import string
import time
import math
from itertools import product

from .main import main, USAGE
from .results import main as show_results
from ..common.clean import clean


MINS = 60
DIR = os.path.dirname(os.path.realpath(__file__))
SIMULATION_TIME = 0.2
CONTROLLER_TYPE = ["strict", "weak"]
EPSILONS = [1e-2, 1e-1]

# fmt: off

# [[rng-params-defs-start]]

RNG_PARAMS = [
    #mu_1,   sigma_1,   mu_2,    sigma_2 (minutes)
    (100,    5,         100,     5),
    (100,    25,        100,     25),
    (100,    5,         50,      5),
    (50,     5,         100,     25),
    (100,    5,         20,      5),
    (20,     5,         100,     25),
]

# [[rng-params-defs-end]]

# fmt: on


def _results(argv):
    output_file = f"{DIR}/result.png"
    args = ["", "-o", output_file]
    show_results(args + argv[1:])

    return 0


def _main(argv):
    log_file = f"{DIR}/results.json"
    with open(log_file, "w") as fh:
        fh.write('{ "trials": [' + os.linesep)

    for eps in EPSILONS:
        for cont in CONTROLLER_TYPE:
            for rng in RNG_PARAMS:
                args = [
                    "",
                    "-o",
                    log_file,
                    "-r",
                    ",".join(map(lambda x: str(x * MINS), rng)),
                    "-T",
                    SIMULATION_TIME,
                    "-C",
                    cont,
                    "-e",
                    str(eps),
                ]
                args += argv[1:]
                print("Starting simulation with arguments:")
                print("  ", args)
                main(args)
                with open(log_file, "a") as fh:
                    fh.write(f",{os.linesep}")

    with open(log_file, "a") as fh:
        fh.write("{}]}" + os.linesep)

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
