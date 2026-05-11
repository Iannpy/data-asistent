"""Scalar formatter for primitive Python types."""

from typing import Any, Dict, Literal, Union


def format_scalar(value: Any) -> Dict[str, Any]:
    """
    Format a scalar value (int, float, string, bool, None) to JSON-compatible dict.

    Args:
        value: The scalar value to format.

    Returns:
        Dict with 'type' and 'value' keys.
    """
    if value is None:
        return {
            "type": "null",
            "value": None,
        }

    if isinstance(value, bool):
        return {
            "type": "boolean",
            "value": value,
        }

    if isinstance(value, int):
        return {
            "type": "integer",
            "value": value,
        }

    if isinstance(value, float):
        return {
            "type": "float",
            "value": value,
        }

    if isinstance(value, str):
        return {
            "type": "string",
            "value": value,
        }

    # Fallback for other types - convert to string
    return {
        "type": "unknown",
        "value": str(value),
    }


def is_scalar(value: Any) -> bool:
    """Check if a value is a scalar (primitive) type."""
    if value is None:
        return True
    if isinstance(value, (bool, int, float, str)):
        return True
    return False