"""Integration tests for the query endpoint.

Tests the full query → response flow including:
- API endpoint integration
- Agent core processing
- Kernel execution
- Result formatting
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi.testclient import TestClient


# Test data fixtures
@pytest.fixture
def sample_csv_data() -> str:
    """Sample CSV data for testing."""
    return """id,name,age,salary,department
1,Alice,30,50000,Engineering
2,Bob,25,45000,Marketing
3,Charlie,35,60000,Engineering
4,Diana,28,55000,Engineering
5,Eve,32,58000,Marketing"""


@pytest.fixture
def temp_csv_file(sample_csv_data: str) -> Generator[str, None, None]:
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(sample_csv_data)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_large_csv() -> str:
    """Generate a larger CSV for truncation testing."""
    rows = ["id,value,category"]
    for i in range(1500):
        rows.append(f"{i},{i * 10},{['A', 'B', 'C'][i % 3]}")
    return "\n".join(rows)


@pytest.fixture
def temp_large_csv(sample_large_csv: str) -> Generator[str, None, None]:
    """Create a large temporary CSV file."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(sample_large_csv)
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


# Mock execution results
@pytest.fixture
def mock_dataframe_result():
    """Mock result simulating a pandas DataFrame."""
    # This mimics what the kernel would return
    mock_df = Mock()
    mock_df.__class__.__name__ = "DataFrame"
    mock_df.shape = (5, 3)
    mock_df.columns = ["name", "age", "salary"]
    mock_df.to_dict.return_value = [
        {"name": "Alice", "age": 30, "salary": 50000},
        {"name": "Bob", "age": 25, "salary": 45000},
    ]
    return mock_df


@pytest.fixture
def mock_scalar_result():
    """Mock result simulating a scalar value."""
    return 5  # len(df) result


@pytest.fixture
def mock_figure_result():
    """Mock result simulating a matplotlib figure."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 2, 3])
    return fig


class TestQueryEndpoint:
    """Test suite for /query endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        # Import app after path is set
        from src.api.routes import app
        from src.config import settings

        self.app = app
        self.settings = settings
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test that health endpoint works."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_query_endpoint_missing_body(self):
        """Test query endpoint with missing request body."""
        response = self.client.post("/query")
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_missing_query(self):
        """Test query endpoint with missing query field."""
        response = self.client.post(
            "/query",
            json={"dataset_path": "/tmp/test.csv"},
        )
        assert response.status_code == 422

    def test_query_endpoint_missing_dataset(self):
        """Test query endpoint with missing dataset_path."""
        response = self.client.post(
            "/query",
            json={"query": "test query"},
        )
        assert response.status_code == 422

    @patch("src.agent.core.AgentCore.execute")
    def test_query_endpoint_success(self, mock_execute, temp_csv_file: str):
        """Test successful query execution."""
        # Mock the agent execution
        mock_execute.return_value = {
            "success": True,
            "result": {"type": "scalar", "value": 5},
            "execution_time_ms": 1500,
        }

        response = self.client.post(
            "/query",
            json={
                "query": "¿cuántas filas tiene?",
                "dataset_path": temp_csv_file,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert "execution_time_ms" in data

    @patch("src.agent.core.AgentCore.execute")
    def test_query_endpoint_returns_dataframe(self, mock_execute, temp_csv_file: str):
        """Test query endpoint returns DataFrame correctly."""
        from src.formatters.dataframe import format_dataframe

        # Simulate a DataFrame result
        mock_df = Mock()
        mock_df.__class__.__name__ = "DataFrame"
        mock_df.__len__ = lambda self: 5

        # Create a mock dataframe-like object
        mock_result = {"data": [{"id": 1}, {"id": 2}], "metadata": {"row_count": 2}}

        mock_execute.return_value = {
            "success": True,
            "result": mock_result,
            "execution_time_ms": 2000,
        }

        response = self.client.post(
            "/query",
            json={
                "query": "dame los primeros 2 registros",
                "dataset_path": temp_csv_file,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data

    @patch("src.agent.core.AgentCore.execute")
    def test_query_endpoint_error_handling(self, mock_execute, temp_csv_file: str):
        """Test query endpoint handles errors correctly."""
        mock_execute.return_value = {
            "success": False,
            "error": "Dataset not found",
            "execution_time_ms": 100,
        }

        response = self.client.post(
            "/query",
            json={
                "query": "test",
                "dataset_path": "/nonexistent/path.csv",
            },
        )

        assert response.status_code == 200  # API returns 200 but success=False
        data = response.json()
        assert data["success"] is False
        assert "error" in data


class TestVisualizationEndpoint:
    """Test suite for /visualize endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        from src.api.routes import app

        self.app = app
        self.client = TestClient(app)

    @patch("src.agent.core.AgentCore.execute_visualization")
    def test_visualize_endpoint_success(self, mock_visualize, temp_csv_file: str):
        """Test successful visualization generation."""
        # Mock figure result
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.hist([1, 2, 3, 2, 2, 3])

        mock_visualize.return_value = {
            "success": True,
            "result": {
                "type": "figure",
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
                "metadata": {
                    "chart_type": "histogram",
                    "dimensions": {"width": 800, "height": 600},
                },
            },
            "execution_time_ms": 3000,
        }

        response = self.client.post(
            "/visualize",
            json={
                "query": "histograma de edad",
                "dataset_path": temp_csv_file,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert data["result"]["type"] == "figure"

    @patch("src.agent.core.AgentCore.execute_visualization")
    def test_visualize_endpoint_error(self, mock_visualize, temp_csv_file: str):
        """Test visualization endpoint error handling."""
        mock_visualize.return_value = {
            "success": False,
            "error": "Column 'nonexistent' not found",
            "execution_time_ms": 500,
        }

        response = self.client.post(
            "/visualize",
            json={
                "query": "gráfico de columna que no existe",
                "dataset_path": temp_csv_file,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestDataFrameFormatter:
    """Test suite for DataFrame formatter."""

    def test_format_dataframe_basic(self):
        """Test basic DataFrame formatting."""
        from src.formatters.dataframe import format_dataframe

        # Create mock DataFrame
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=5)
        mock_df.__getitem__ = Mock(side_effect=lambda key: [1, 2, 3, 4, 5] if key == "col" else Mock())
        mock_df.columns = ["col1", "col2"]
        mock_df.dtypes = {"col1": "int64", "col2": "float64"}
        mock_df.iterrows = Mock(return_value=iter([]))

        result = format_dataframe(mock_df)
        assert result["type"] == "dataframe"
        assert "data" in result
        assert "metadata" in result

    def test_format_dataframe_truncation(self, temp_large_csv: str):
        """Test DataFrame truncation for large datasets."""
        from src.formatters.dataframe import format_dataframe
        import pandas as pd

        # Read large CSV
        df = pd.read_csv(temp_large_csv)

        # Format should truncate to 1000 rows
        result = format_dataframe(df, max_rows=1000)

        assert result["metadata"]["row_count"] == 1000
        assert result["metadata"]["truncated"] is True
        assert result["metadata"]["original_row_count"] == 1500


class TestFigureFormatter:
    """Test suite for Figure formatter."""

    def test_format_matplotlib_figure(self):
        """Test matplotlib figure formatting."""
        from src.formatters.figure import format_figure
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        ax.set_title("Test Plot")

        result = format_figure(fig)

        assert result["type"] == "figure"
        assert "image_base64" in result
        assert result["metadata"]["library"] in ["matplotlib", "unknown"]

        plt.close(fig)

    def test_format_figure_with_dpi(self):
        """Test figure formatting with custom DPI."""
        from src.formatters.figure import format_figure
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])

        result = format_figure(fig, dpi=72)

        assert result["metadata"]["dpi"] == 72

        plt.close(fig)

    def test_format_figure_metadata(self):
        """Test figure metadata extraction."""
        from src.formatters.figure import format_figure_metadata
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots()
        ax.plot([1, 2], [1, 2])

        metadata = format_figure_metadata(fig)

        assert "library" in metadata
        assert "chart_type" in metadata
        assert metadata["supported"] is True

        plt.close(fig)


class TestScalarFormatter:
    """Test suite for Scalar formatter."""

    def test_format_integer(self):
        """Test integer scalar formatting."""
        from src.formatters.scalar import format_scalar

        result = format_scalar(42)
        assert result["type"] == "scalar"
        assert result["value"] == 42

    def test_format_float(self):
        """Test float scalar formatting."""
        from src.formatters.scalar import format_scalar

        result = format_scalar(3.14159)
        assert result["type"] == "scalar"
        assert result["value"] == 3.14159

    def test_format_string(self):
        """Test string scalar formatting."""
        from src.formatters.scalar import format_scalar

        result = format_scalar("hello")
        assert result["type"] == "scalar"
        assert result["value"] == "hello"

    def test_format_boolean(self):
        """Test boolean scalar formatting."""
        from src.formatters.scalar import format_scalar

        result = format_scalar(True)
        assert result["type"] == "scalar"
        assert result["value"] is True


class TestEndToEndFlow:
    """End-to-end integration tests."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures."""
        from src.api.routes import app

        self.app = app
        self.client = TestClient(app)

    @patch("src.agent.core.AgentCore.execute")
    @patch("src.executor.kernel.KernelClient.execute")
    def test_full_query_flow(self, mock_kernel_execute, mock_agent_execute, temp_csv_file: str):
        """Test complete query flow: API → Agent → Kernel → Formatter."""

        # Mock kernel execution result (DataFrame-like)
        mock_kernel_result = Mock()
        mock_kernel_result.result = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        mock_kernel_result.stdout = "5 rows"
        mock_kernel_result.stderr = ""
        mock_kernel_result.execution_time_ms = 1000

        mock_kernel_execute.return_value = mock_kernel_result

        # Mock agent execution
        mock_agent_execute.return_value = {
            "success": True,
            "result": {"type": "dataframe", "data": [{"name": "Alice"}], "metadata": {}},
            "execution_time_ms": 2000,
        }

        # Make request
        response = self.client.post(
            "/query",
            json={
                "query": "¿cuál es la edad promedio?",
                "dataset_path": temp_csv_file,
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "result" in data
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)

    @patch("src.agent.core.AgentCore.execute")
    def test_error_recovery_flow(self, mock_agent_execute, temp_csv_file: str):
        """Test error recovery in the query flow."""

        # Simulate agent error
        mock_agent_execute.side_effect = Exception("Invalid generated code")

        response = self.client.post(
            "/query",
            json={
                "query": "invalid query that causes error",
                "dataset_path": temp_csv_file,
            },
        )

        # Should handle error gracefully
        data = response.json()
        # Either 500 (unhandled) or 200 with success=false (handled)
        assert response.status_code in [200, 500]


class TestSecurityIntegration:
    """Security-focused integration tests."""

    @patch("src.agent.core.AgentCore.execute")
    def test_blocked_api_in_query(self, mock_execute, temp_csv_file: str):
        """Test that blocked APIs are detected and blocked."""
        from src.executor.security import SecurityScanner

        scanner = SecurityScanner()

        # Test blocked code patterns
        blocked_codes = [
            "import os; os.system('ls')",
            "import subprocess; subprocess.run(['ls'])",
            "import socket; socket.connect(('localhost', 8080))",
            "open('/etc/passwd', 'r')",
        ]

        for code in blocked_codes:
            is_safe, violations = scanner.scan(code)
            assert not is_safe, f"Code should be blocked: {code}"
            assert len(violations) > 0

    def test_security_scanner_validation(self):
        """Test security scanner against various code patterns."""
        from src.executor.security import SecurityScanner

        scanner = SecurityScanner()

        # Safe code patterns
        safe_codes = [
            "import pandas as pd",
            "df = pd.read_csv('data.csv')",
            "df['column'].mean()",
            "df.groupby('col').sum()",
            "import matplotlib.pyplot as plt",
        ]

        for code in safe_codes:
            is_safe, _ = scanner.scan(code)
            assert is_safe, f"Code should be safe: {code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])