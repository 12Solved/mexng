SHELL := /bin/bash
MAKE_SCRIPTS := scripts/make

.PHONY: init update run-app kill-app poll-mail process-mail run-mail clean-mail test

## Initialize the project from 0 — run after your first git pull/clone.
init:
	@bash $(MAKE_SCRIPTS)/init.sh

## Install new dependencies and migrate the db — run after every git pull.
update:
	@bash $(MAKE_SCRIPTS)/update.sh

## Run the app (db + backend + frontend dev servers).
run-app:
	@bash $(MAKE_SCRIPTS)/run-app.sh

## Stop the app (backend + frontend dev servers + db).
kill-app:
	@bash $(MAKE_SCRIPTS)/kill-app.sh

## Run the mail poller once.
poll-mail:
	@bash $(MAKE_SCRIPTS)/poll-mail.sh

## Run the mail processor once.
process-mail:
	@bash $(MAKE_SCRIPTS)/process-mail.sh

## Poll then process mail.
run-mail:
	@bash $(MAKE_SCRIPTS)/run-mail.sh

## Delete all emails/attachments and reset all mail checkpoints. Use FORCE=1 to skip the prompt.
clean-mail:
	@bash $(MAKE_SCRIPTS)/clean-mail.sh

## Run the test suite (template — fill in as tests get added).
test:
	@bash $(MAKE_SCRIPTS)/test.sh
