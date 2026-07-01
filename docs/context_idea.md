## Main idea:

* Rather than having raw dictionaries everywhere, make a workflow context object because this gives a more unified way of passing context.
```py
class WorkflowContext:
    def __init__(self):
        self.data = {}

    def set(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)

    def has(self, key):
        return key in self.data
```
* Step now has args_in and args_out, which can help with validation.
* Config comes from the frontend which directly gives a json object with directions for the workflow.
```py
class Step:
    args_in = {}
    args_out = []

    def __init__(self, **config):
        self.config = config

    def execute(self, context):
        raise NotImplementedError()
```
* Let's say this is the received json:
```json
workflow_json = {
    "steps": [
        {
            "type": "ExtractLanguages"
        },
        {
            "type": "SaveInFolder",
            "base": "/incoming",
            "context_path": "languages"
        }
    ]
}
```
* "type" is what step does the workflow do. "base" is the directory of the main folder.
* "context_path" is a dynamic path that can change during the results of the previous step.
* So if you have a method that extracts languages like this:
```py
class ExtractLanguages(Step):

    args_in = {
        "email": "required"
    }

    args_out = ["languages"]

    def execute(self, context):
        email = context.get("email")  #This grabs the context of the email

        if "German" in email:
            language = "German"
        else:
            language = "English"

        context.set("languages",language) # This sets a new value with a key
```
* It will set up the new context in the Context object
* So now let's say you have a SaveInFolder configured step that expects a dynamic path from the config file.
```py
class SaveInFolder(Step):

    args_in = {
        "email": "required"
    }

    args_out = ["folder", "folder_created"]

    def execute(self, context):

        base = self.config["base"] # This picks up the base directory
        context_path = self.config["context_path"] # This picks up what kind of context it needs, in this case "languages"

        dynamic_part = context.get(context_path) # this gets the current language in the context

        folder = f"{base}/{dynamic_part}"

        context.set("folder",folder)
        context("folder_created", true)
```
* Now whenever the backend gets the json object it tries to build it while getting the needed steps from the registry
```py
class WorkflowEngine:

    def __init__(self, workflow_json):
        self.steps = self._build_steps(workflow_json)

    def _build_steps(self, workflow_json):
        steps = []

        for step_data in workflow_json["steps"]:
            step_type = step_data["type"] # Pick up the type of step from the json body

            step_class = STEP_REGISTRY[step_type] # Try to find it in the registry

            config = {k: v for k, v in step_data.items() if k != "type"} # Get out the configurations for the steps while skipping the type

            step_instance = step_class(**config) # Create the step instance with the configuration

            steps.append(step_instance) # Add it to the list of configured steps

        return steps

    def run(self, initial_context):
        context = WorkflowContext(initial_context) # Pick up the context from the object

        for step in self.steps: # Iterate through the steps while validating if all the context is there
            self._validate(step, context)
            step.execute(context)

        return context

    def _validate(self, step, context):
        for key, requirement in step.args_in.items():
            if requirement == "required" and key not in context: # Check if the required context exists, if not throw exception
                raise Exception(f"Missing required input: {key}")
```