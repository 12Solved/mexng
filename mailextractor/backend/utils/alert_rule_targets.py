"""
Alert rule filters come in pairs: an exact filter and its regex alternative.
A rule may set only one of each pair.
"""

# (exact filter, pattern alternative)
TARGET_PAIRS = (
    ("event_type", "event_type_pattern"),
    ("workflow_id", "workflow_name_pattern"),
    ("checkpoint_id", "checkpoint_name_pattern"),
)

PATTERN_FIELDS = tuple(pattern for _, pattern in TARGET_PAIRS)


def check_targets(values: dict) -> None:
    """Raise ValueError if `values` sets both halves of any pair."""
    conflicts = [
        f"{exact}/{pattern}"
        for exact, pattern in TARGET_PAIRS
        if values.get(exact) is not None and values.get(pattern) is not None
    ]
    if conflicts:
        raise ValueError(f"Set either the exact filter or the pattern, not both: {', '.join(conflicts)}")
