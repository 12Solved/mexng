from mailextractor.app.steps.registry import STEPS, load_steps

load_steps("mailextractor.app.steps")
# Later: load_steps_from_path(user_steps_dir, source="user")

STEP_REGISTRY = STEPS