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