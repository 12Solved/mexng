#!/bin/bash
# Wipes all mail data from the db (emails, attachments) and resets every
# mail-related checkpoint (mailbox poll state, workflow checkpoints, and the
# on-disk poller checkpoint files) back to their fresh-start state.
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
for f in "$CHECKPOINT_PATH" read_email_checkpoint.txt; do
	if [ -f "$f" ]; then
		printf '{"dt": null, "hash": null}' > "$f"
		echo "Reset $f"
	fi
done

echo "clean-mail complete."
