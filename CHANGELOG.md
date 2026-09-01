# Changelog

Notes on notable commits, newest first. Started 2026-09-01 — earlier history is not backfilled.

## feat: rework Makefile into scripts/make/, add update and clean-mail targets (2026-09-01)

16 files changed: 14 added, 0 deleted, 2 modified.

**Makefile**
- `Makefile`: now a thin dispatcher — every target just calls a script under `scripts/make/`. Renamed targets to be more descriptive: `setup`→`init`, `dev`→`run-app`, `down`→`kill-app`, `poll`→`poll-mail`, `process`→`process-mail`, `run`→`run-mail`. AdWded `update` (installs new deps + migrates db, for after `git pull`) and `clean-mail` (see below).

**scripts/make/ (all added)**
- `_common.sh`: shared `ROOT_DIR` + `activate_env()` helper (source venv, nenv, `.env`).
- `db-up.sh` / `db-down.sh`: docker-compose wrappers for the mailextractor Postgres container.
- `migrate.sh`: `alembic upgrade head`.
- `init.sh`: first-time setup from 0 — creates `.env`/`.venv`/`.nenv`/frontend deps if missing, brings db up, migrates.
- `update.sh`: `pip install`/`npm install` + migrate, idempotent, meant to run after every `git pull`.
- `run-app.sh` / `kill-app.sh`: same behavior as the old `dev`/`down` targets (db up + `webserver-dev.sh`; pkill uvicorn/vite + db down).
- `poll-mail.sh` / `process-mail.sh` / `run-mail.sh`: same behavior as the old `poll`/`process`/`run` targets.
- `clean_mail.py` / `clean-mail.sh`: new — deletes all `emails` rows (attachments cascade via existing FK), clears `mailbox_state`, resets the `checkpoints` table's runtime fields (`status`→`never_seen`, timestamps→`NULL`, config columns untouched), and resets the on-disk `checkpoint.txt`/`read_email_checkpoint.txt` poller checkpoint files to `{"dt": null, "hash": null}`. Prompts `y/N` before running; `FORCE=1` skips the prompt.
- `test.sh`: placeholder — runs `pytest tests/` if a suite exists under `tests/`, otherwise just says so (no test suite exists yet).

**Bugfix**
- Every script above computes its own directory into a variable that, in an earlier draft, was named `DIR`. `.nenv/bin/activate` (nodeenv) also sets an unscoped `DIR` when sourced, so `source .nenv/bin/activate` inside a script silently clobbered that script's own `$DIR` for anything called afterward (e.g. `update.sh` failed with `bash: .../.nenv/bin/migrate.sh: No such file or directory`). Renamed to `MAKE_DIR` everywhere to avoid the collision.

**Docs**
- `README.md`: added a "Makefile" section documenting all targets; updated the `make poll` reference to `make poll-mail`; noted the `make run-app`/`make poll-mail && make process-mail`/`make run-mail` shortcuts next to the manual commands.

## feat: poller processor refactor (2026-09-01)

19 files changed: 3 added, 2 deleted, 14 modified.

**Poller**
- `mailextractor/app/poller/provider.py` (added): new `BaseProvider`/`IMAPProvider`/`GLOBProvider` hierarchy with a shared `dt`/`hash` checkpoint file (read/write helpers, retry logic for IMAP batch fetches).
- `mailextractor/app/poller/providers/imap_provider.py` (deleted): old UID/UIDVALIDITY-based IMAP provider, superseded by `provider.py`'s `IMAPProvider`.
- `mailextractor/app/poller/providers/gmail_provider.py` (deleted): Gmail OAuth provider removed entirely — Gmail is no longer a supported `EMAIL_PROVIDER`.
- `mailextractor/app/poller/poller.py` (rewritten): dropped the old CLI (`--filter`, `--batch-size`, `--from-uid`, `--reset`), the Gmail code path, and DB-backed `MailboxState` (UIDVALIDITY) tracking. Now iterates `provider.iterate_mails()`, commits once per poll run, and advances the checkpoint file.
- `mailextractor/app/poller/email_inserter.py`: module docstring only, no logic change.
- `scripts/poller.py` (added): thin CLI entrypoint calling `poller.main()`.
- `scripts/poller.sh` (rewritten): now just calls `scripts/poller.py`. Dropped `--loop`, `--batch`, `--interval`, `--filter`, `--batch-size`, `--start-offset`, `--batch-delay` — no equivalent replacement.
- `scripts/read_email.py` (rewritten): now sets `EMAIL_PROVIDER=glob` and a persistent `CHECKPOINT_PATH=read_email_checkpoint.txt`, delegating to `poller.main()` instead of its own standalone import logic.

**Processor**
- `mailextractor/app/processor/processor.py` (added): extracts `scripts/process.py`'s workflow-run logic into reusable functions (`get_workflows_from_db`, `get_emails_from_db`, `get_re_run_workflow_ids_from_db`, `get_run_groups`, `run_db`, `run_dry`, `process`, `main`).
- `scripts/process.py` (gutted): now a thin wrapper calling `processor.main()`.

**Config / docs**
- `mailextractor/app/config.py`: added `GLOB_PATTERNS` and `CHECKPOINT_PATH` settings. `EMAIL_PROVIDER` default was left at `"gmail"` despite Gmail support being removed.
- `.env.example`, `.env.prod.example`: documented the `imap`/`glob`/`msga` provider options (`msga` was never implemented).
- `README.md`: added an "Email Providers" section documenting `imap`/`glob` and the checkpoint mechanism; updated run instructions to `python -m mailextractor.app.poller.poller` + `python mailextractor/app/processor/processor.py`.
- `.gitignore`: added `.ipynb_checkpoints/`, `_dep_*`, `/dev.ipynb`, `/checkpoint.txt`, `/read_email_checkpoint.txt`.
- `Makefile` (added): `setup`, `dev`, `db-up`/`db-down`, `migrate`, `poll`, `process`, `run` targets.
- `requirements.txt`: added `O365` (unused).

**Misc**
- `mailextractor/models.py`: added `Email.__repr__`.
- `mailextractor/app/workflow.py`: added `Workflow.__repr__`.
- `mailextractor/app/workflow_context.py`: added `WorkflowContext.__repr__`.
