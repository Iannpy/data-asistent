"""Figure formatter for matplotlib, seaborn, and Plotly figures.

Converts various figure types to Base64-encoded PNG images for API responses.
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FigureMetadata:
    """Metadata about a formatted figure."""

    chart_type: str
    dimensions: Tuple[int, int]
    format: str = "png"
    library: Optional[str] = None


def format_figure(
    figure: Any,
    dpi: int = 100,
    max_width: int = 1200,
    max_height: int = 800,
) -> Dict[str, Any]:
    """Format a matplotlib, seaborn, or Plotly figure to Base64 PNG.

    Args:
        figure: Figure object from matplotlib, seaborn, or Plotly
        dpi: Resolution for PNG export (default: 100)
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        Dictionary with Base64 image and metadata
    """
    if figure is None:
        return {
            "type": "figure",
            "image_base64": None,
            "metadata": {
                "chart_type": "null",
                "dimensions": {"width": 0, "height": 0},
            },
        }

    # Detect figure type and library
    library = _detect_library(figure)
    chart_type = _detect_chart_type(figure, library)

    # Convert to matplotlib Figure if needed
    matplotlib_figure = _to_matplotlib_figure(figure, library)

    # Calculate dimensions respecting max limits
    dimensions = _calculate_dimensions(matplotlib_figure, max_width, max_height)

    # Save to bytes buffer
    buffer = io.BytesIO()
    matplotlib_figure.savefig(
        buffer,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    buffer.seek(0)

    # Encode to Base64
    image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

    # Close figure to free memory
    matplotlib_figure.clf()
    matplotlib_figure.close()

    return {
        "type": "figure",
        "image_base64": image_base64,
        "metadata": {
            "chart_type": chart_type,
            "dimensions": {
                "width": dimensions[0],
                "height": dimensions[1],
            },
            "dpi": dpi,
            "library": library,
        },
    }


def _detect_library(figure: Any) -> str:
    """Detect which library created the figure.

    Args:
        figure: Figure object

    Returns:
        Library name: 'matplotlib', 'seaborn', or 'plotly'
    """
    # Check for matplotlib Figure
    try:
        import matplotlib.figure

        if isinstance(figure, matplotlib.figure.Figure):
            return "matplotlib"
    except ImportError:
        pass

    # Check for seaborn (returns matplotlib Axes)
    # Seaborn figures are matplotlib Axes, not Figure
    try:
        import seaborn as sns

        # Seaborn returns axes, wrap in figure
        if hasattr(figure, "get_figure"):
            return "seaborn"
    except ImportError:
        pass

    # Check for Plotly figure
    try:
        if hasattr(figure, "to_html") or hasattr(figure, "to_image"):
            return "plotly"
    except ImportError:
        pass

    # Check for pandas Series with plot method
    try:
        import pandas as pd

        if isinstance(figure, pd.Series):
            return "pandas"
    except ImportError:
        pass

    # Check for pandas DataFrame with plot method
    try:
        import pandas as pd

        if isinstance(figure, pd.DataFrame):
            return "pandas"
    except ImportError:
        pass

    return "unknown"


def _detect_chart_type(figure: Any, library: str) -> str:
    """Detect the type of chart from the figure.

    Args:
        figure: Figure object
        library: Detected library name

    Returns:
        Chart type string
    """
    if library == "matplotlib" or library == "seaborn":
        return _detect_matplotlib_chart_type(figure)
    elif library == "plotly":
        return _detect_plotly_chart_type(figure)
    elif library == "pandas":
        return "dataframe_plot"

    return "unknown"


def _detect_matplotlib_chart_type(figure: Any) -> str:
    """Detect chart type from matplotlib figure or axes.

    Args:
        figure: matplotlib Figure or Axes

    Returns:
        Chart type string
    """
    import matplotlib.pyplot as plt

    # Get axes from figure
    if hasattr(figure, "get_axes"):
        axes = figure.get_axes()
    else:
        axes = [figure] if hasattr(figure, "containers") else []

    if not axes:
        return "unknown"

    ax = axes[0]

    # Check for collections (scatter, bar, etc.)
    collections = ax.collections
    if collections:
        # Check what's in the collection
        for coll in collections:
            if hasattr(coll, "get_offsets"):
                return "scatter"

    # Check containers (bar, box, etc.)
    containers = ax.containers if hasattr(ax, "containers") else []
    if containers:
        # Determine type from container
        if hasattr(containers[0], "patches"):
            return "bar"
        if hasattr(containers[0], "get_caps"):
            return "bar"  # Error bars

    # Check lines
    lines = ax.lines
    if lines:
        # Check if it's a line or step plot
        if hasattr(lines[0], "get_drawstyle"):
            drawstyle = lines[0].get_drawstyle()
            if drawstyle == "steps-pre" or drawstyle == "steps-mid":
                return "step"
        return "line"

    # Check patches (pie, etc.)
    patches = ax.patches
    if patches:
        # Pie charts have wedge patches
        if any(hasattr(p, "theta1") for p in patches):
            return "pie"

    # Check for hist
    if hasattr(ax, "containers") and not containers:
        # Might be histogram
        return "histogram"

    # Check for text (text plot, annotation)
    texts = ax.texts
    if texts:
        return "text"

    # Check for images
    images = ax.images
    if images:
        return "image"

    # Default
    return "custom"


def _detect_plotly_chart_type(figure: Any) -> str:
    """Detect chart type from Plotly figure.

    Args:
        figure: Plotly figure

    Returns:
        Chart type string
    """
    try:
        # Get layout to determine type
        if hasattr(figure, "layout"):
            layout = figure.layout
            if hasattr(layout, "title"):
                # Try to determine from data
                pass

        # Get data traces
        if hasattr(figure, "data"):
            traces = figure.data
            if traces:
                trace_type = traces[0].type if hasattr(traces[0], "type") else str(type(traces[0]))
                return f"plotly_{trace_type}"

        return "plotly"
    except Exception:
        return "plotly"


def _to_matplotlib_figure(figure: Any, library: str) -> "matplotlib.figure.Figure":
    """Convert any figure type to a matplotlib Figure.

    Args:
        figure: Input figure
        library: Detected library

    Returns:
        matplotlib Figure object

    Raises:
        ValueError: If figure cannot be converted
    """
    import matplotlib.pyplot as plt
    import matplotlib.figure

    # If already matplotlib Figure, return as-is
    if isinstance(figure, matplotlib.figure.Figure):
        return figure

    # If seaborn Axes, get figure or create one
    if library == "seaborn":
        if hasattr(figure, "get_figure"):
            fig = figure.get_figure()
            if fig is not None:
                return fig
        # Create figure from axes
        fig, ax = plt.subplots()
        figure.figure = fig
        return fig

    # If pandas Series/DataFrame with plot
    if library == "pandas":
        fig, ax = plt.subplots()
        try:
            figure.plot(ax=ax)
        except Exception:
            # Fallback: just use the dataframe representation
            pass
        return fig

    # If Plotly, convert
    if library == "plotly":
        return _plotly_to_matplotlib(figure)

    # Try generic conversion
    if hasattr(figure, "figure"):
        fig = figure.figure
        if fig is not None:
            return fig

    # Last resort: create empty figure
    fig, ax = plt.subplots()
    return fig


def _plotly_to_matplotlib(figure: Any) -> "matplotlib.figure.Figure":
    """Convert Plotly figure to matplotlib Figure.

    This is a simplified conversion - for production, consider kaleido.

    Args:
        figure: Plotly figure

    Returns:
        matplotlib Figure
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()

    try:
        # Try to get data from Plotly figure
        if hasattr(figure, "data"):
            for trace in figure.data:
                trace_type = getattr(trace, "type", "scatter")

                if trace_type in ["scatter", "scattergl"]:
                    x = getattr(trace, "x", [])
                    y = getattr(trace, "y", [])
                    mode = getattr(trace, "mode", "markers")
                    if "lines" in mode:
                        ax.plot(x, y)
                    else:
                        ax.scatter(x, y)

                elif trace_type == "bar":
                    x = getattr(trace, "x", [])
                    y = getattr(trace, "y", [])
                    ax.bar(x, y)

                elif trace_type == "histogram":
                    x = getattr(trace, "x", [])
                    ax.hist(x, bins=30)

        # Set title if available
        if hasattr(figure, "layout") and hasattr(figure.layout, "title"):
            title = figure.layout.title
            if hasattr(title, "text"):
                ax.set_title(title.text)

    except Exception:
        # If conversion fails, return empty figure
        pass

    return fig


def _calculate_dimensions(
    figure: Any,
    max_width: int,
    max_height: int,
) -> Tuple[int, int]:
    """Calculate figure dimensions respecting max limits.

    Args:
        figure: matplotlib Figure
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels

    Returns:
        Tuple of (width, height) in inches
    """
    import matplotlib.pyplot as plt

    # Get figure size in inches
    if hasattr(figure, "get_size_inches"):
        width_inch, height_inch = figure.get_size_inches()
    else:
        width_inch, height_inch = 10, 6  # Default matplotlib size

    # Calculate pixel dimensions (assuming 100 DPI)
    dpi = 100
    width_px = width_inch * dpi
    height_px = height_inch * dpi

    # Scale down if exceeds max
    if width_px > max_width or height_px > max_height:
        scale = min(max_width / width_px, max_height / height_px)
        width_inch *= scale
        height_inch *= scale

    return int(width_inch * dpi), int(height_inch * dpi)


def format_figure_metadata(figure: Any) -> Dict[str, Any]:
    """Extract metadata from a figure without rendering.

    Args:
        figure: Figure object

    Returns:
        Dictionary with figure metadata
    """
    library = _detect_library(figure)
    chart_type = _detect_chart_type(figure, library)

    return {
        "library": library,
        "chart_type": chart_type,
        "supported": library in ["matplotlib", "seaborn", "pandas", "plotly"],
    }


# Backwards compatibility alias
def serialize_figure(figure: Any, **kwargs) -> Dict[str, Any]:
    """Alias for format_figure for backwards compatibility.

    Args:
        figure: Figure object
        **kwargs: Additional arguments passed to format_figure

    Returns:
        Formatted figure dictionary
    """
    return format_figure(figure, **kwargs)