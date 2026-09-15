#!/bin/bash
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

activate_env
python mailextractor/app/poller/poller.py
