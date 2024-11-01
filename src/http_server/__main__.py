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
from ..pi_controller import results as pi_controller_results

DIR = os.path.dirname(os.path.realpath(__file__))
MEAN_VALS = [0.1]
CONT = ["SN", "UV"]
TOTAL_PRODUCED = 1024 * 4
AB_CONCURRENCY = [1, 2, 4, 8, 16, 32, 64]


def _results(argv):
    output_file = f"{DIR}/result.png"
    args = ["", "-o", output_file]
    show_results(args + argv[1:])

    return 0


def _main(argv):
    ab_path = shutil.which("ab")
    if ab_path is None:
        raise RuntimeError(
            "This simulation requires 'ab' command from apache2-utils package."
        )

    with open(DIR + "/test.txt", "w") as fh:
        i = 1024
        while i > 0:
            fh.write(random.SystemRandom().choice(string.ascii_uppercase))
            i -= 1

    ab_cmd = ["/bin/bash", f"{DIR}/start_ab.sh"]
    ab_cmd += [f"{TOTAL_PRODUCED}", f"{DIR+'/test.txt'}", "http://localhost:5000/"]

    uv_cmd = ["/bin/bash", f"{DIR}/test_uvicorn.sh"]

    results_fh = open(DIR + "/results.txt", "w")
    results_fh.truncate(0)

    log_file = f"{DIR}/results.json"
    with open(log_file, "w") as fh:
        fh.write('{ "trials": [' + os.linesep)

    for c, j_ac, mean in product(CONT, enumerate(AB_CONCURRENCY), MEAN_VALS):
        j, ac = j_ac
        csv_fn = f"{DIR}/result_{c}_{ac}_{j}.csv"
        proc = subprocess.Popen(ab_cmd + [str(ac), csv_fn, c], stdout=results_fh)

        if c != "UV":
            args = ["", "-o", log_file, "-A", str(proc.pid), "-C", ac, "-c", c]
            args += argv[1:]
            print("Starting simulation with arguments:")
            print("  ", args)
            main(args)
            with open(log_file, "a") as fh:
                fh.write(f",{os.linesep}")
        else:
            subprocess.call(uv_cmd + [str(proc.pid), str(ac)])

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
