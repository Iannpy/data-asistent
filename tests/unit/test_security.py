"""Unit tests for security scanner.

Tests AST-based code scanning for security violations.
Blacklist patterns: os, subprocess, socket, etc.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.executor.security import (
    SecurityScanner,
    ScanResult,
    quick_scan,
    SYSTEM_MODULES,
    DANGEROUS_FUNCTIONS,
    DANGEROUS_ATTRIBUTES,
)


class TestSecurityScannerBlacklist:
    """Tests for blacklist patterns."""

    def test_blocks_os_import(self):
        """Test that os module import is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("import os")
        assert not result.safe
        assert any("os" in v[1].lower() for v in result.violations)

    def test_blocks_subprocess_import(self):
        """Test that subprocess module import is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("import subprocess")
        assert not result.safe
        assert any("subprocess" in v[1].lower() for v in result.violations)

    def test_blocks_socket_import(self):
        """Test that socket module import is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("import socket")
        assert not result.safe
        assert any("socket" in v[1].lower() for v in result.violations)

    def test_blocks_requests_import(self):
        """Test that requests module import is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("import requests")
        assert not result.safe

    def test_blocks_pickle_import(self):
        """Test that pickle module import is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("import pickle")
        assert not result.safe

    def test_blocks_system_function(self):
        """Test that os.system() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("os.system('ls')")
        assert not result.safe
        assert any("system" in v[1].lower() for v in result.violations)

    def test_blocks_subprocess_run(self):
        """Test that subprocess.run() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("subprocess.run(['ls'])")
        assert not result.safe

    def test_blocks_exec(self):
        """Test that exec() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("exec('print(1)')")
        assert not result.safe
        assert any("exec" in v[1].lower() for v in result.violations)

    def test_blocks_eval(self):
        """Test that eval() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("eval('1+1')")
        assert not result.safe
        assert any("eval" in v[1].lower() for v in result.violations)

    def test_blocks_open_function(self):
        """Test that open() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("open('file.txt')")
        assert not result.safe

    def test_blocks_open_file(self):
        """Test that file() call is blocked."""
        scanner = SecurityScanner()
        result = scanner.scan("file('test')")
        assert not result.safe


class TestSecurityScannerSafeCode:
    """Tests for safe code patterns."""

    def test_allows_pandas_import(self):
        """Test that pandas import is allowed."""
        scanner = SecurityScanner()
        result = scanner.scan("import pandas as pd")
        assert result.safe

    def test_allows_numpy_import(self):
        """Test that numpy import is allowed."""
        scanner = SecurityScanner()
        result = scanner.scan("import numpy as np")
        assert result.safe

    def test_allows_matplotlib_import(self):
        """Test that matplotlib import is allowed."""
        scanner = SecurityScanner()
        result = scanner.scan("import matplotlib.pyplot as plt")
        assert result.safe

    def test_allows_pandas_usage(self):
        """Test that pandas operations are allowed."""
        scanner = SecurityScanner()
        code = """
import pandas as pd
df = pd.read_csv('/data/test.csv')
print(df.head())
"""
        result = scanner.scan(code)
        assert result.safe

    def test_allows_dataframe_operations(self):
        """Test that DataFrame operations are allowed."""
        scanner = SecurityScanner()
        code = """
df['price'].mean()
df[df['status'] == 'active'].count()
df.groupby('category')['sales'].sum()
"""
        result = scanner.scan(code)
        assert result.safe

    def test_allows_matplotlib_figures(self):
        """Test that matplotlib figure creation is allowed."""
        scanner = SecurityScanner()
        code = """
import matplotlib.pyplot as plt
import io

fig, ax = plt.subplots()
ax.plot([1, 2, 3], [4, 5, 6])
buf = io.BytesIO()
fig.savefig(buf, format='png')
"""
        result = scanner.scan(code)
        assert result.safe


class TestSecurityScannerEdgeCases:
    """Edge case tests for security scanner."""

    def test_empty_code(self):
        """Test that empty code is considered safe."""
        scanner = SecurityScanner()
        result = scanner.scan("")
        assert result.safe

    def test_whitespace_only(self):
        """Test that whitespace-only code is safe."""
        scanner = SecurityScanner()
        result = scanner.scan("   \n\n   ")
        assert result.safe

    def test_none_input(self):
        """Test that None input is handled gracefully."""
        scanner = SecurityScanner()
        result = scanner.scan(None)
        assert result.safe

    def test_syntax_error(self):
        """Test that syntax errors are detected."""
        scanner = SecurityScanner()
        result = scanner.scan("import (")
        assert not result.safe
        assert any("syntax" in v[0].lower() for v in result.violations)

    def test_whitelist_custom_pattern(self):
        """Test that whitelisted patterns are allowed."""
        scanner = SecurityScanner(whitelist=["os.path"])
        result = scanner.scan("from os.path import join")
        assert result.safe


class TestQuickScan:
    """Tests for quick_scan utility function."""

    def test_quick_scan_safe_code(self):
        """Test quick_scan returns True for safe code."""
        assert quick_scan("import pandas as pd") is True

    def test_quick_scan_unsafe_code(self):
        """Test quick_scan returns False for unsafe code."""
        assert quick_scan("import os") is False
        assert quick_scan("os.system('ls')") is False


class TestASTScannerIntegration:
    """Integration tests for AST scanner with mocked scenarios."""

    @patch("src.executor.security.SecurityScanner._check_node")
    def test_check_node_called_for_all_nodes(self, mock_check):
        """Test that _check_node is called for all AST nodes."""
        mock_check.return_value = []
        scanner = SecurityScanner()
        scanner.scan("import pandas as pd")

        # Should have been called multiple times
        assert mock_check.call_count > 0

    def test_complex_pandas_code(self):
        """Test complex but safe pandas analysis code."""
        scanner = SecurityScanner()
        code = """
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('/data/sales.csv')

# Basic stats
total_sales = df['amount'].sum()
avg_price = df['price'].mean()

# Grouped analysis
monthly = df.groupby(df['date'].dt.month)['sales'].agg(['sum', 'mean', 'count'])

# Filter and transform
active_df = df[df['status'] == 'active'].copy()
active_df['discount'] = active_df['price'] * 0.1

# Result
result = {
    'total_sales': total_sales,
    'avg_price': avg_price,
    'monthly_stats': monthly.to_dict()
}
"""
        result = scanner.scan(code)
        assert result.safe

    def test_malicious_code_attempts(self):
        """Test various malicious code patterns are blocked."""
        scanner = SecurityScanner()
        malicious_patterns = [
            "import os; os.system('rm -rf /')",
            "import subprocess; subprocess.run('ls')",
            "import socket; socket.socket()",
            "__import__('os').system('ls')",
            "eval('__import__(\"os\").system(\"ls\")')",
            "exec('import os')",
        ]

        for code in malicious_patterns:
            result = scanner.scan(code)
            assert not result.safe, f"Should have blocked: {code}"
