# Changelog

Notes on notable commits, newest first. Started 2026-09-01 — earlier history is not backfilled.

## feat: restore continuous polling via --loop (2026-09-01)

Review item #11 — `poller.sh` dropped the old `--loop` capability with no
replacement; nothing in the repo scheduled repeated polling.

`poller.py` gains `--loop`/`--interval` (default 300s), mirroring
`scripts/check_checkpoints.py`'s existing APScheduler pattern (same library,
same SIGTERM/SIGINT shutdown handling). A failed poll inside the loop is
logged and retried next interval rather than crashing the process — so
Group 2's skip_hashes recovery works without needing a manual restart.
`poller.sh` passes args through again. `make poll-mail` stays one-shot,
matching `check_checkpoints.py` (no make target either); looping is opt-in
via the raw script. `--batch`/IMAP-filter mode stays dropped, as agreed.

Verified live: `--loop --interval 2` ticked 3 times against the real
mailbox, then shut down cleanly on SIGTERM (exit 0).

## feat: checkpoint-bypass for full backfill (2026-09-01)

Review item #7. `CHECKPOINT_PATH=""` (or `checkpoint_path=None` on a
provider directly) now means "no checkpoint" — every dt/hash/skip_hashes
filter becomes a no-op and `update_checkpoint()` no-ops too, so a run always
(re-)inserts everything it's given instead of persisting any state.

`scripts/read_email.py` now sets `CHECKPOINT_PATH=""` instead of a shared
`read_email_checkpoint.txt`, restoring the old backfill script's "always
insert the given files" behavior — re-running it on the same files re-inserts
them rather than silently skipping already-seen dates. Removed the now-dead
`read_email_checkpoint.txt` gitignore entry and local file. Verified live:
running it twice on the same fixture inserted it twice, no checkpoint file created.

## fix: default EMAIL_PROVIDER to imap, drop dead config/model (2026-09-01)

Review items #4, #16, #8. `config.py`: default `EMAIL_PROVIDER` was still
`"gmail"` though Gmail support was removed (get_provider() rejects it) —
deploys that didn't set it explicitly crashed on startup. Defaults to
`"imap"` now. Also removed `GMAIL_CREDENTIALS_PATH`/`GMAIL_TOKEN_PATH`
(confirmed dead — GmailProvider is gone, nothing reads these).

`models.py`: removed `MailboxState` (confirmed dead — the checkpoint-file
mechanism replaced it, nothing references it anymore) plus its now-unused
`UniqueConstraint` import. New migration `2bb9e6b0bb89` drops the
`mailbox_state` table; verified both directions (upgrade drops it, downgrade
recreates it) against the dev db. `tests/conftest.py`'s truncate list updated
to match.

Dead-code cleanup, review items #9, #12: removed the unreachable `return None`
after `raise` in `IMAPProvider._parse_message`. Removed unused imports in
`poller.py` — `argparse` (flagged by the review) plus `math`/`time` (same
issue, not individually called out).

`processor.py` (#13, #14): `get_run_groups`'s mutable default arg
(`re_run_workflow_ids={}`) fixed to `None` + guard. `run_dry()` was dead code
with no per-workflow error isolation, unlike `run_db()` — kept and fixed
(matching try/except), no caller wired up yet since none exists to wire it
to. Also dropped a duplicate `from mailextractor.app.config import config`.
New `tests/test_processor.py` proves one workflow raising doesn't stop the
rest of the group from running.

## feat: poison-pill skip-list + fix IMAP None-date crash (2026-09-01)

Review items (`_dev_review.txt` #1, #2, #3, #6).

- Checkpoint gained `skip_hashes: list[str]`, hand-edited by an operator to
  unwedge a poller stuck crashing on the same bad email every poll — checked
  before any content-specific failure, so it covers any reason, not just #2.
  For a file that fails to parse entirely (glob, #6), no content hash exists
  yet, so it's skip-listed by `sha256(file_path)` instead.
- Bug caught by the new tests: `update_checkpoint()` read `skip_hashes` back
  *inside* `open(cp, "w")`, which truncates on open — every write silently
  wiped the skip-list. Fixed (read before opening for write).
- IMAPProvider (#2): `parsed['date'] < dt` had no None guard (GLOBProvider
  already did) — an unparseable Date header raised a raw `TypeError` inside
  the retry loop, silently dropping the batch instead of reaching poll()'s
  crash.
- poller.py (#1): missing-date crash now logs the email's hash/message_id
  under `POISON_PILL_EMAIL` so it can be found and skip-listed.
- poller.py (#3): comment only, no behavior change — same-second timestamp
  collisions accepted as rare enough to ignore.
- `tests/test_poller_skip_list.py` (new, 3 tests) — caught the truncation bug above.
- `README.md`: documented the skip-list workflow.

## fix: persist poller checkpoint across prod redeploys (2026-09-01)

Review item (`_dev_review.txt` #15, flagged HIGHEST PRIORITY): the prod
backend stored `checkpoint.txt` inside the container with no volume, so every
redeploy lost it, IMAP's `SINCE` filter fell back to fetching the entire
mailbox history, and (no unique constraint on `Email.message_id`) that meant
mass-duplicate inserts on every redeploy.

- `Dockerfile`: pinned the `mex` user to a fixed `uid=1000 gid=1000` (was
  `-r`/auto-assigned, and conflicted with `-r`'s system-UID range once pinned
  — dropped `-r`) so an operator can `chown` a host bind mount to a known
  owner ahead of time. Added `mkdir -p /app/data`.
- `docker-compose.prod.yml`: backend service now bind-mounts `./data` (host)
  to `/app/data` (container) — a directory mount rather than mounting the
  checkpoint file directly, so Group 2's later skip-list data has somewhere
  to live alongside it, and so a missing host file doesn't trip Docker's
  create-a-directory-instead footgun.
- `.env.prod.example`: added `CHECKPOINT_PATH=/app/data/checkpoint.txt` —
  previously unset, defaulting to relative `checkpoint.txt` (i.e.
  `/app/checkpoint.txt`), which wasn't under any mount.
- `.gitignore`: added `/data/` for the host-side bind mount contents.
- `README.md`: documented `mkdir -p data && chown 1000:1000 data` as a
  required first-deploy step under Production Deployment.

Verified by building the image and bind-mounting a host dir: the non-root
`mex` user (uid 1000) successfully wrote `checkpoint.txt` into it.

## feat: add poll/process pipeline tests (2026-09-01)

**tests/ (new)**
- `conftest.py`: creates/reuses a fixed-name `db_test` Postgres database (same server as `DATABASE_URL`, independent of the dev db's actual name) and truncates all tables before each test. Provides `make_config` (a plain config object injected into `poll()`/`process()`/`get_provider()`, which already take config as a parameter — no monkeypatching of the real `.env`-backed config singleton needed) and `insert_workflow`/`load_workflows` helpers; the latter loads `example-data/workflows/*.json` and rewrites any `save_attachment_step` destination into `tmp_path` so tests don't write into `./out/...` in the repo.
- `test_poll_process_glob.py`: polls the real `example-data/emails/*.eml` fixtures via the glob provider, runs them through `date_step_invoice.json` and `sender_recipient_filter.json`, and asserts on actual outcomes (run success + saved attachment, a matching-sender/recipient run succeeding, a non-matching one landing `skipped`, re-poll idempotency). A second test confirms the deliberately-broken `no_date_header.eml` fixture makes `poll()` raise and roll back the entire batch.
- `test_poll_process_imap.py`: polls the real mailbox from `.env` (checkpoint seeded to 7 days ago to keep each run bounded), runs whatever's found through a filter-free probe workflow, and asserts every fetched email ends up with exactly one terminal-state run plus re-poll idempotency. Skips automatically if `IMAP_USERNAME`/`IMAP_PASSWORD` aren't set.
- `requirements.txt`: added `pytest`.

**Bugfix**
- `.gitignore` had a blanket `tests/` entry (presumably a stale placeholder from before any test suite existed) which would have silently excluded the entire new `tests/` directory from git. Removed it; kept the unrelated `pytest.ini`/`requirements-test.txt`/`ruff.*` placeholder entries.

**Docs**
- `.gitignore`: added `db_test.sql`/`db_test.dump` for local dump/backup artifacts of the `db_test` test database.
- `README.md`: added a "Testing" section under the Makefile docs describing the `db_test` database and what the glob/IMAP tests cover.

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
