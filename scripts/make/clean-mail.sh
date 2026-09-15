#!/bin/bash
# Wipes all mail data from the db (emails, attachments) and resets every
# mail-related checkpoint (workflow checkpoints and the on-disk poller
# checkpoint file) back to their fresh-start state.
set -e
MAKE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
source "$MAKE_DIR/_common.sh"
cd "$ROOT_DIR"

if [ -z "$FORCE" ]; then
	read -r -p "This deletes ALL emails/attachments and resets all mail checkpoints. Continue? [y/N] " reply
	case "$reply" in
		[yY][eE][sS]|[yY]) ;;
		*) echo "Aborted."; exit 1 ;;
	esac
fi

activate_env

python "$MAKE_DIR/clean_mail.py"

CHECKPOINT_PATH="${CHECKPOINT_PATH:-checkpoint.txt}"
if [ -f "$CHECKPOINT_PATH" ]; then
	printf '{"dt": null, "hash": null, "skip_hashes": []}' > "$CHECKPOINT_PATH"
	echo "Reset $CHECKPOINT_PATH"
fi

echo "clean-mail complete."
