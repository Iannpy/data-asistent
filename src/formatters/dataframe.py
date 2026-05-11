"""DataFrame formatter with type preservation and row truncation.

Converts pandas DataFrames to JSON-compatible dictionaries while preserving
column types and limiting output size.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from src.config import settings


# Type mapping from pandas to JSON-compatible types
PANDAS_TO_JSON_TYPES: Dict[str, str] = {
    "int64": "integer",
    "int32": "integer",
    "int16": "integer",
    "int8": "integer",
    "uint64": "integer",
    "uint32": "integer",
    "uint16": "integer",
    "uint8": "integer",
    "float64": "float",
    "float32": "float",
    "float16": "float",
    "bool": "boolean",
    "object": "string",
    "string": "string",
    "datetime64[ns]": "datetime",
    "datetime64[ns, tz]": "datetime",
    "timedelta64[ns]": "duration",
    "category": "string",
}


@dataclass
class DataFrameMetadata:
    """Metadata about a formatted DataFrame."""

    row_count: int
    column_count: int
    column_types: Dict[str, str]
    truncated: bool
    original_row_count: Optional[int] = None
    columns_included: Optional[List[str]] = None
    columns_excluded: Optional[List[str]] = None


def get_column_type(dtype: Any) -> str:
    """Get the JSON-compatible type string for a pandas dtype.

    Args:
        dtype: pandas dtype

    Returns:
        Type string
    """
    dtype_name = str(dtype)

    # Check for exact match first
    if dtype_name in PANDAS_TO_JSON_TYPES:
        return PANDAS_TO_JSON_TYPES[dtype_name]

    # Check for partial match (e.g., "int64" in "int64[ns]")
    for pandas_type, json_type in PANDAS_TO_JSON_TYPES.items():
        if pandas_type in dtype_name:
            return json_type

    # Default to string for unknown types
    return "string"


def format_dataframe(
    df: Any,
    max_rows: Optional[int] = None,
    max_columns: Optional[int] = None,
    include_types: bool = True,
) -> Dict[str, Any]:
    """Format a pandas DataFrame to a JSON-compatible dictionary.

    Args:
        df: pandas DataFrame to format
        max_rows: Maximum rows to include (default from settings)
        max_columns: Maximum columns to include (default: all)
        include_types: Whether to include column types in output

    Returns:
        Dictionary with formatted data and metadata
    """
    if df is None:
        return {
            "type": "dataframe",
            "data": [],
            "metadata": {
                "row_count": 0,
                "column_count": 0,
                "truncated": False,
            },
        }

    max_rows = max_rows or settings.dataset_max_rows
    row_count = len(df)
    column_count = len(df.columns)

    # Check for truncation
    truncated = row_count > max_rows
    rows_to_include = min(row_count, max_rows)

    # Get column information
    columns = list(df.columns)
    column_types = {
        col: get_column_type(df[col].dtype) for col in columns
    }

    # Apply column limit
    columns_included = columns
    columns_excluded: List[str] = []

    if max_columns and column_count > max_columns:
        columns_included = columns[:max_columns]
        columns_excluded = columns[max_columns:]
        column_count = max_columns

    # Convert to records with type preservation
    data: List[Dict[str, Any]] = []

    for idx in range(rows_to_include):
        row = df.iloc[idx]
        record: Dict[str, Any] = {}

        for col in columns_included:
            value = row[col]

            # Handle missing values
            if value is None or (hasattr(value, "isna") and value.isna()):
                record[col] = None
                continue

            # Convert based on type
            dtype_name = str(df[col].dtype)

            if "int" in dtype_name:
                record[col] = int(value)
            elif "float" in dtype_name:
                # Handle NaN values
                if value != value:  # NaN check
                    record[col] = None
                else:
                    record[col] = float(value)
            elif "bool" in dtype_name:
                record[col] = bool(value)
            elif "datetime" in dtype_name:
                # Convert to ISO format string
                if hasattr(value, "isoformat"):
                    record[col] = value.isoformat()
                else:
                    record[col] = str(value)
            else:
                # String and other types
                record[col] = str(value)

        data.append(record)

    # Build output
    result: Dict[str, Any] = {
        "type": "dataframe",
        "data": data,
    }

    # Add metadata
    metadata: Dict[str, Any] = {
        "row_count": rows_to_include,
        "column_count": column_count,
        "column_types": {k: v for k, v in column_types.items() if k in columns_included},
        "truncated": truncated,
    }

    if truncated:
        metadata["original_row_count"] = row_count
        metadata["message"] = f"Showing first {max_rows} rows of {row_count}"

    if columns_excluded:
        metadata["columns_excluded"] = columns_excluded
        metadata["columns_included"] = columns_included

    result["metadata"] = metadata

    return result


def format_dataframe_summary(df: Any) -> Dict[str, Any]:
    """Format a summary of a DataFrame (without data rows).

    Args:
        df: pandas DataFrame

    Returns:
        Dictionary with DataFrame summary
    """
    if df is None:
        return {
            "type": "dataframe_summary",
            "metadata": {
                "row_count": 0,
                "column_count": 0,
            },
        }

    column_types = {
        col: get_column_type(df[col].dtype) for col in df.columns
    }

    return {
        "type": "dataframe_summary",
        "metadata": {
            "row_count": len(df),
            "column_count": len(df.columns),
            "column_types": column_types,
            "columns": list(df.columns),
            "index": {
                "type": get_column_type(df.index.dtype) if df.index is not None else "integer",
                "name": df.index.name,
            },
        },
    }


def detect_result_type(result: Any) -> str:
    """Detect the type of a kernel execution result.

    Args:
        result: Result from kernel execution

    Returns:
        Type string: 'dataframe', 'figure', 'scalar', 'unknown'
    """
    if result is None:
        return "null"

    # Check for DataFrame
    try:
        import pandas as pd
        if isinstance(result, pd.DataFrame):
            return "dataframe"
        if isinstance(result, pd.Series):
            return "series"
    except ImportError:
        pass

    # Check for matplotlib figure
    try:
        import matplotlib.figure
        if isinstance(result, matplotlib.figure.Figure):
            return "figure"
    except ImportError:
        pass

    # Check for Plotly figure
    try:
        if hasattr(result, "to_html"):  # Plotly figure
            return "figure"
    except ImportError:
        pass

    # Check for scalar types
    if isinstance(result, (int, float, str, bool)):
        return "scalar"

    # Check for dict/list (likely DataFrame-like)
    if isinstance(result, dict):
        if "type" in result:
            return result["type"]
        return "dict"
    if isinstance(result, list):
        return "list"

    return "unknown"


def auto_format(result: Any) -> Dict[str, Any]:
    """Automatically format a result based on its type.

    Args:
        result: Kernel execution result

    Returns:
        Formatted result dictionary
    """
    result_type = detect_result_type(result)

    if result_type == "dataframe":
        return format_dataframe(result)
    elif result_type == "scalar":
        from src.formatters.scalar import format_scalar
        return format_scalar(result)
    elif result_type == "figure":
        from src.formatters.figure import format_figure
        return format_figure(result)
    elif result_type == "null":
        return {"type": "null", "value": None}
    else:
        # Fallback: try to convert to string
        return {
            "type": result_type,
            "value": str(result),
        }
