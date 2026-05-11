"""Formatters package."""

from src.formatters.scalar import format_scalar, is_scalar
from src.formatters.dataframe import (
    format_dataframe,
    format_dataframe_summary,
    auto_format,
    detect_result_type,
)

__all__ = [
    "format_scalar",
    "is_scalar",
    "format_dataframe",
    "format_dataframe_summary",
    "auto_format",
    "detect_result_type",
]
