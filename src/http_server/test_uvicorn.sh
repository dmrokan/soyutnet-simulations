#!/bin/bash

set -eux -o pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

python3 "$SCRIPT_DIR/uvicorn_main.py" $1 $2
