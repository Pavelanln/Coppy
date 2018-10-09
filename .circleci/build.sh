#!/bin/bash

set -ex

script_path=$(python -c "import os; import sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")
top_dir=$(dirname $(dirname "$script_path"))

exec "$top_dir/scripts/onnx/install-develop.sh"

