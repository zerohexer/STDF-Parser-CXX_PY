#!/bin/bash
# Cross-platform STDF parser test launcher

# Set library path for Linux/WSL
export LD_LIBRARY_PATH="$PWD/cpp/third_party/lib:$LD_LIBRARY_PATH"

# Run the test
python3 test_parser.py "$@"