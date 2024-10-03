# SPDX-License-Identifier:  CC-BY-SA-4.0

import os
from pathlib import Path
import glob


COMMON_DIR = os.path.dirname(os.path.realpath(__file__))
COMMON_PATH = Path(COMMON_DIR).resolve()
SRC_PATH = Path("/".join(COMMON_PATH.parts[:-1])).resolve()


def is_path_valid(p):
    p1 = p.resolve()

    return Path("/".join(p1.parts + ("..",))).resolve() == SRC_PATH


def clean(DIR):
    if not is_path_valid(Path(DIR)):
        raise RuntimeError(f"Can not clean path '{DIR}'")

    ignored = []
    with open(DIR + "/.gitignore", "r") as fh:
        line = " "
        while line:
            line = fh.readline()
            if line.startswith("!"):
                ignored.append(line[1:].strip())

    files = glob.glob(DIR + "/*")
    for f in files:
        p = Path(f)
        if p.is_file() and p.name not in ignored:
            p.unlink()
