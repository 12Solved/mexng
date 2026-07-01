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

Filter and control-flow steps (`ProviderFilterStep`, `AttachmentPatternStep`, `ForEachStep`) run normally — dry run only suppresses effects, not routing logic.

**Result shape** (per workflow):
- `stopped: false`, `error: null` — ran to completion, would have had effects
- `stopped: true`, `error: null` — filtered out early (`@stop` set), no effects expected
- `error: string` — workflow threw an exception

The `runs` table is never touched. Logs are still written.
