# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
import sys
import shutil
import subprocess
import random
import string
import time
import math

from .main import main, USAGE
from .results import main as show_results
from ..pi_controller import results as pi_controller_results

DIR = os.path.dirname(os.path.realpath(__file__))
MEAN_VALS = [0.01]
K_PIS = ["1e-2,1e-4"]
CONT = ["none", "C1", "C2"]
TOTAL_PRODUCED = 1000
AB_CONCURRENCY = [1] + list(range(8, 8 * 24 + 1, 8))


def _results(argv):
    output_file = f"{DIR}/result.png"
    args = ["", "-o", output_file]
    show_results(args + argv[1:])

    pi_controller_results.main(
        ["", "-i", f"{DIR}/results_1.json", "-o", f"{DIR}/result_0.png"]
    )

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

    results_fh = open(DIR + "/results.txt", "w")
    results_fh.truncate()

    i = 1
    for k in K_PIS:
        log_file = f"{DIR}/results_{i}.json"
        with open(log_file, "w") as fh:
            fh.write('{ "trials": [' + os.linesep)

        for c in CONT:
            j = 0
            for ac in AB_CONCURRENCY:
                for mean in MEAN_VALS:
                    csv_fn = f"{DIR}/result_{i}_{c}_{ac}_{j}.csv"
                    proc = subprocess.Popen(
                        ab_cmd + [str(ac), csv_fn, c], stdout=results_fh
                    )

                    args = [
                        "",
                        "-c",
                        c,
                        "-r",
                        f"exponential,{mean}",
                        "-o",
                        log_file,
                        "-K",
                        k,
                        "-T",
                        TOTAL_PRODUCED * 4 * mean,
                        "-A",
                        str(proc.pid),
                        "-C",
                        ac,
                    ]
                    args += argv[1:]
                    print("Starting simulation with arguments:")
                    print("  ", args)
                    main(args)
                    with open(log_file, "a") as fh:
                        fh.write(f",{os.linesep}")
                    j += 1

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
    case _:
        sys.exit(_main(["main"] + sys.argv[1:]))
