#!/bin/bash
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"

docker-compose -f "$ROOT_DIR/mailextractor/docker-compose.yml" down
