import importlib
import logging
import pkgutil

from mailextractor.app.steps.STEP_CATEGORIES import STEP_CATEGORIES

# type key -> step class
STEPS = {}

# Modules in the steps package that don't define steps
_NON_STEP_MODULES = {"base_step", "registry", "STEP_REGISTRY", "STEP_CATEGORIES"}


def register(cls, source="builtin"):
  step_type = cls.type

  # Built-in keys stay dot-free so "namespace.name" is free for user-defined steps later
  if source == "builtin" and "." in step_type:
    raise ValueError(f"{cls.__name__}: built-in step type '{step_type}' must not contain '.'")

  if cls.category not in STEP_CATEGORIES:
    logging.getLogger(cls.__name__).error(f"{cls.__name__}: category '{cls.category}' is not in STEP_CATEGORIES")
    raise ValueError(f"{cls.__name__}: category '{cls.category}' is not in STEP_CATEGORIES")

  existing = STEPS.get(step_type)
  if existing is not None:
    # The same class seen twice (e.g. a module re-import) is harmless
    if _qualified_name(existing) == _qualified_name(cls):
      return
    raise ValueError(
      f"Step type '{step_type}' is already registered by {_qualified_name(existing)}, "
      f"cannot register {_qualified_name(cls)}"
    )

  cls.source = source
  STEPS[step_type] = cls


def load_steps(package_name):
  """Imports every module in the package; step classes register themselves on import."""
  package = importlib.import_module(package_name)
  for module_info in pkgutil.iter_modules(package.__path__):
    if module_info.name in _NON_STEP_MODULES:
      continue
    importlib.import_module(f"{package_name}.{module_info.name}")


def _qualified_name(cls):
  return f"{cls.__module__}.{cls.__qualname__}"
