#!/bin/bash

set -eux -o pipefail

echo "Controller $6"
sleep 6 && ab -n "$1" -p "$2" -c "$4" -e "$5" "$3"

echo ""
echo "======================================="
echo ""
