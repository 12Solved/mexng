# Changelog

Notes on notable commits, newest first. Started 2026-09-01 at commit `2ebbea3` — earlier history is not backfilled.

## 2ebbea3 — feat: poller processor refactor (2026-09-01)

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
