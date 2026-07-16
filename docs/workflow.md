## Workflow configuration

* Workflow is defined in the database.
* Workflow contains an ordered list step names like for an example:
```py
["parse", "decrypt", "map"]
```
* Users can add or edit the list.
* Every workflow step implements a common interface:
```py
execute(data, context)
```
* Each step is modular and independent.

## Step registration

* All available steps are registered in a central registry.
* The registry maps step names like ("parse") to their implementation class.

## Workflow execution

* The system fetches emails that are not yet processed.
* The workflow loads the configured step list.
* For each step the workflow retrieves the step from the registry, executes the step and passes the output to the next step.

## Example

* The workflow is defined in the DB like this:
```json
[
  {
    "name": "check_sender",
    "params": { "domain": "gmx.de" }
  },
  {
    "name": "check_attachment",
    "params": { "pattern": "hello*.pdf" }
  },
  {
    "name": "save_attachment",
    "params": { "directory": "/gmx_emails/" }
  }
]
```
* The workflow has configurable steps like these:
```py
class CheckSenderStep:
  def execute(self, email, context):
    required_domain = context["domain"]

    sender = extract_email_address(email.sender)
    domain = sender.split("@")[-1]

    if domain != required_domain:
        return None

    return email
```
```py
class CheckAttachmentStep:
  def execute(self, email, context):
    pattern = context["pattern"]

    for attachment in email.attachments:
      if matches_pattern(attachment.filename, pattern):
        context["matched_attachment"] = attachment
        return email

    return None
```
```py
class SaveAttachmentStep:
  def execute(self, email, context):
    attachment = context["matched_attachment"]
    directory = context["directory"]

    date_str = format_date(email.date)
    new_name = f"hello-{date_str}.pdf"

    save_file(directory + new_name, attachment.content)

    return email
```
* How the workflow engine calls the steps:
```py
for step_config in workflow_steps:
  step = registry.get(step_config["name"])
  email = step.execute(email, step_config["params"])

  if email is None:
    break
```

## How context flows currently

Current implementation places different choices of context to use in configurations of workflows.

```py
"global": {
    "email": "Email",
    "email_id": "int",
    "email_subject": "string",
    "email_sender": "string",
    "email_recipient": "string",
    "date": "string",
    "timestamp": "string",
},
"foreach": {
    "current": "Attachment",
    "attachment_name": "string",
    "ext": "string",
    "content_type": "string",
    "attachment_size": "int",
}
```

While configuring workflow steps, the user will have a choice to use different context variables in their filename templates, destinations etc.
The list of available variables will be at the bottom of the configuration side panel. There are two types of context in the list. One is guaranteed that it will be available and the other one is from previously inserted workflow steps.
Currently the implemenetation forces the user to you use this pattern ```${VARIABLE_NAME}``` for inserting dynamic naming. This is because the resolver needs this pattern to insert the needed variables from the context.

Examples:
* ```${attachment_name}-data```
* ```${attachment_name}-${date}-${email_sender}```

## Date computation (`date_step`)

`DateStep` computes a date/time and stores it in context as a string, so it
can be reused later via `${output_var}` (e.g. in a `save_attachment_step`
destination or filename template).

Config:

| Field           | Default          | Meaning |
|-----------------|------------------|---------|
| `source`        | `now`            | `now`, `email_date` (the email's `Date` header), an explicit ISO 8601 string, or a `${variable}` reference to one already in context |
| `offset_days`   | `0`              | integer, may be negative |
| `offset_hours`  | `0`              | integer, may be negative |
| `format`        | `%Y-%m-%d`       | Python `strftime` pattern |
| `output_var`    | `computed_date`  | context key the result is stored under — editable so multiple `date_step` instances can coexist in one workflow |

If `source=email_date` and the email has no date, the step logs a warning
and sets `@stop`, skipping the rest of that (sub-)workflow branch rather
than failing the run. A malformed `source`/offset/format is treated as a
config error and raises.

Examples (`config`):

```json
{ "source": "now", "format": "%Y%m%d" }
```
→ `computed_date = "20260714"`

```json
{ "source": "email_date", "offset_days": -1, "format": "%Y-%m-%d", "output_var": "prev_day" }
```
→ `prev_day` = the day before the email's date, e.g. `"2026-07-13"`

```json
{ "source": "email_date", "format": "%B %d, %Y" }
```
→ `computed_date = "July 14, 2026"`

Chaining two instances to get both an invoice date and a due date 7 days later:

```json
[
  { "type": "date_step", "config": { "source": "email_date", "output_var": "invoice_date" } },
  { "type": "date_step", "config": { "source": "email_date", "offset_days": 7, "output_var": "due_date" } },
  { "type": "save_attachment_step", "config": {
      "destination": "/invoices/${invoice_date}",
      "filename_template": "invoice-due-${due_date}"
  } }
]
```

## Setting variables (`set_variable_step`)

`SetVariableStep` writes a literal or resolved value into a context key. This step lets the
user pick both the key and the value, so it can set ordinary variables
(`invoice_id`, `region`, ...) or reserved control keys (`@stop`, `@dry_run`).

Config:

| Field           | Default   | Meaning |
|-----------------|-----------|---------|
| `name`          | —         | required. Context key to set, e.g. `invoice_id` or `@dry_run` |
| `value`         | —         | required. Literal value or a `${variable}` reference to one already in context |
| `value_type`    | `string`  | `string`, `boolean`, `integer`, or `float`. Coerces the resolved value before storing it |
| `only_if_unset` | `false`   | if `true`, skip the assignment when `name` is already present in context |

**Security note — control keys are not restricted.** `name` accepts any
string, including `@stop` and `@dry_run`, with no allowlist. This mirrors how
`run_options` supplied through the run API is already merged into context
unfiltered (`workflow.py`), so this step does not introduce a new privilege —
but it does make it easy for a workflow author to change control flow (skip
the rest of a branch, or silently disable disk writes) from deep inside a
step list. Review workflows that use `set_variable_step` on `@`-prefixed keys
with the same care as the run-time `@dry_run` toggle.

Use `value_type: "boolean"` for control flags: string values are always
truthy in Python, so writing the literal string `"false"` to `@dry_run`
without coercion would leave dry-run **on**. Accepted boolean literals
(case-insensitive): `true`/`1`/`yes`/`on`/`enable`/`enabled` and
`false`/`0`/`no`/`off`/`disable`/`disabled`.

Examples (`config`):

```json
{ "name": "invoice_id", "value": "${email_subject}" }
```

```json
{ "name": "@dry_run", "value": "disable", "value_type": "boolean" }
```
`context["@dry_run"] = False`, so later steps that check
`context.get("@dry_run")` treat this run as live rather than dry-run.

```json
{ "name": "region", "value": "eu", "only_if_unset": "true" }
```
only sets `region` if no earlier step already set it.

## Address filtering (`match_sender_address_step`, `match_recipient_address_step`)

Replaces the old `provider_filter_step` (domain-suffix-only, `From` header
only). Both steps match with a case-insensitive regex (`re.search`) rather
than a fixed substring/suffix check, and both `@stop` the branch on no match.
See `docs/mailglob.txt` / `docs/notes.md` for the legacy Perl `mail_glob`
behavior these steps are modeled after.

`MatchSenderAddressStep` checks the email's `From` address:

| Field     | Default | Meaning |
|-----------|---------|---------|
| `pattern` | —       | required. Regex matched against the sender's address (`user@domain`, display name stripped) |

Sets `sender_address` in context on match.

```json
{ "type": "match_sender_address_step", "config": { "pattern": "@.*example\\.com$" } }
```

`MatchRecipientAddressStep` checks a recipient header — `To`, `Cc`, `Bcc`,
`X-Original-To`, or all four at once:

| Field     | Default | Meaning |
|-----------|---------|---------|
| `header`  | `To`    | `To`, `Cc`, `Bcc`, `X-Original-To`, or `Any (To, Cc, Bcc, X-Original-To)` |
| `pattern` | —       | required. Regex matched against each candidate address found in the selected header(s) |

Each header may contain multiple comma-separated addresses; the step checks
all of them and matches on the first one satisfying `pattern`. With
`header: "Any (...)"`, this mirrors `mail_glob`'s `to_regex || cc_regex ||
x_original_to_regex` OR logic. `To` is read from the email's stored
`recipient` column; `Cc`/`Bcc`/`X-Original-To` are read from `raw_headers`
(only present if the mail server actually sent that header — there is no
`Received`-header-derived fallback like the legacy Seppmail-specific trick in
`mail_glob`).

Sets `recipient_address` in context on match.

```json
{ "type": "match_recipient_address_step", "config": { "header": "Any (To, Cc, Bcc, X-Original-To)", "pattern": "bank.*@" } }
```

## Archive extraction (`extract_archive_step`)

If the current attachment's filename matches `archive_pattern`, extracts its
members in memory (trying no password, then each configured password in
order) and stores them in context — same shape as `email.attachments`, so a
nested `foreach` can feed them straight into `attachment_pattern_step`/
`save_attachment_step`. Otherwise, or if every password fails, `output_var`
is set to `[]` and the branch continues rather than stopping.

Shells out to `7z` (matching `mailglob.txt`'s approach), same as the Perl
original — the attachment is written to a temp file, extracted flat
(basename-only, no member paths) into a temp dir via `7z e`, and the temp
dir is removed afterwards. Since `7z` detects format from file content
rather than the filename, pointing `archive_pattern` at e.g. `*.7z` or
`*.tar.gz` works without any code change — only the entry-point filename
check is pattern-based, not the extraction itself.

Config:

| Field             | Default                | Meaning |
|-------------------|-------------------------|---------|
| `archive_pattern` | `*.zip`                 | Unix-style wildcard deciding whether `current` is treated as an archive |
| `passwords`       | (empty)                 | Comma-separated list, tried in order after an unencrypted attempt |
| `output_var`      | `extracted_attachments` | Context key the extracted member list is stored under |
| `max_depth`       | `5`                     | Caps recursion into archives found inside archives (zip-of-zip) |
| `max_seconds`     | `60`                    | Aborts a single archive's extraction attempt if `7z` runs longer than this |

Requires the `7z` binary on `PATH` (`p7zip-full` in the Docker image); a
missing binary logs a distinct `ARCHIVE_TOOL_MISSING` event rather than
looking like a bad password.

Example — mirrors `reporting_xyz`'s encrypted-zip-to-CSV feed from
`docs/mailglob.txt`:

```json
[
  { "type": "extract_attachment_step" },
  { "type": "foreach", "over": "attachments", "steps": [
      { "type": "extract_archive_step", "config": { "passwords": "secret1,secret2" } },
      { "type": "foreach", "over": "extracted_attachments", "steps": [
          { "type": "attachment_pattern_step", "config": { "pattern": "*_CRESCHZZEKH_SecurityPositions.csv" } },
          { "type": "save_attachment_step", "config": {
              "destination": "./out/bank-light",
              "filename_template": "BANKZRHPositionFile_${date}.csv"
          } }
      ]}
  ]}
]
```