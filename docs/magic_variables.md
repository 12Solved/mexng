# Magic Variables

## Stop Flag

Setting `context.set("@stop", True)` inside a step halts execution — all remaining steps are skipped.

The flag is checked **before each step** in the loop. If it is `True` at that point, the step is not executed and the loop breaks immediately.

Inside a `ForEachStep`, `@stop` is reset to `False` before each iteration (and again after the loop finishes), so one rejected item doesn't block the rest.

After the run, `stop=True` results in `RunState.skipped`; otherwise `RunState.success`.

## Workflow Run States

A workflow run can be in one of the following states:

- **Running** — the run is currently in progress
- **Success** — completed normally (last step had `stop=False`)
- **Failed** — an error occurred (exception raised during execution)
- **Skipped** — last step had `stop=True`
- **Rerun** — set from the UI to re-execute a previous run

## Dry Run

Triggered from the UI via **"Dry run all workflows"** on the single email view. Calls `POST /emails/{id}/runs/dry-run` directly — no `WorkflowRun` rows are created or modified.

`@dry_run: True` is seeded into `WorkflowContext` at the start of each run. Effectful steps check this flag and skip their side effects (file writes, DB updates, etc.) while still setting output keys (e.g. `saved_path`) so downstream steps behave faithfully.

Filter and control-flow steps (`MatchSenderAddressStep`, `MatchRecipientAddressStep`, `AttachmentPatternStep`, `ForEachStep`) run normally — dry run only suppresses effects, not routing logic.

**Result shape** (per workflow):
- `stopped: false`, `error: null` — ran to completion, would have had effects
- `stopped: true`, `error: null` — filtered out early (`@stop` set), no effects expected
- `error: string` — workflow threw an exception

The `runs` table is never touched. Logs are still written.

## Event Type Prefixes

Every log's `event_type` starts with a prefix naming the component that emitted it, e.g. `POLLER_IMAP_AUTH_FAILED`. The prefix is a single word (no inner `_`), so it is always the text before the first `_`, and sorting event types alphabetically groups them by component.

Event types are plain string constants in `mailextractor/app/app_logging/event_types.py`, not an enum; log calls reference them (`extra={"event_type": event_types.POLLER_IMAP_AUTH_FAILED}`) instead of inline strings. When adding a new one, define it there with the prefix of the module it's logged from. To offer it in the alert rule editor before it has ever been logged, also add it to `ALERTABLE_EVENT_TYPES`.

| Prefix | Emitted by |
|---|---|
| `POLLER_` | `app/poller/` — poller, IMAP/GLOB providers, email inserter |
| `PROCESSOR_` | `app/processor/processor.py` — per-email workflow runner |
| `WORKFLOW_` | `app/workflow.py` — workflow engine |
| `STEP_` | `app/steps/` — all steps, including `BaseStep` lifecycle events |
| `CHECKPOINTS_` | `scripts/check_checkpoints.py` |
| `MAINLOOP_` | `scripts/main_loop.py` |
| `CHECKLOGS_` | `scripts/check_logs.py` |

`UNKNOWN` is the fallback when a log call sets no `event_type`; it intentionally has no prefix so missing event types stand out.
