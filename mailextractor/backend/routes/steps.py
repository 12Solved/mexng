import inspect

from fastapi import APIRouter, HTTPException

from mailextractor.app.steps.STEP_CATEGORIES import STEP_CATEGORIES
from mailextractor.app.steps.STEP_REGISTRY import STEP_REGISTRY

router = APIRouter(tags=["steps"])

def _introspect_step(step_type: str, step_class) -> dict:
    category = getattr(step_class, "category", "general")
    return {
        "type": step_type,
        "label": step_class.__name__,
        "docstring": inspect.getdoc(step_class),
        "args_in": getattr(step_class, "args_in", {}),
        "args_out": getattr(step_class, "args_out", []),
        "config_schema": getattr(step_class, "config_schema", {}),
        "category": category,
        "colors": STEP_CATEGORIES.get(category, STEP_CATEGORIES["general"]),
    }

@router.get("/context-vars")
def get_context_vars():
    return {
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
        },
    }

@router.get("/steps")
def list_steps():
    return [
        _introspect_step(step_type, step_class)
        for step_type, step_class in STEP_REGISTRY.items()
    ]

@router.get("/steps/{step_type}")
def get_step(step_type: str):
    if step_type not in STEP_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Step '{step_type}' not found")
    return _introspect_step(step_type, STEP_REGISTRY[step_type])
