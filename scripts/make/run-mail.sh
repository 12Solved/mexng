#!/bin/bash
# Polls then processes mail.
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

bash "$MAKE_DIR/poll-mail.sh"
bash "$MAKE_DIR/process-mail.sh"
