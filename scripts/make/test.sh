#!/bin/bash
# Test runner template — wire up the real suite as tests get added under tests/.
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

source .venv/bin/activate

if ls tests/test_*.py &> /dev/null 2>&1; then
	pytest tests "$@"
else
	echo "No tests found yet under tests/ — this is a placeholder target."
fi
