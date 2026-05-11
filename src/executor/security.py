"""AST-based security scanner for code execution.

Scans Python code using AST to detect potentially dangerous operations.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List, Set, Tuple


# Blacklisted modules and functions that could be used for system access
SYSTEM_MODULES: Set[str] = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "urllib3",
    "http",
    "ftplib",
    "telnetlib",
    "telnet",
    "smtplib",
    "poplib",
    "imaplib",
    "nntplib",
    "xmlrpc",
    "multiprocessing",
    "threading",
    "concurrent",
    "asyncio",
    "thread",
    "process",
    "resource",
    "signal",
    "pty",
    "tty",
    "termios",
    "fcntl",
    "grp",
    "pwd",
    "spwd",
    "crypt",
    "nis",
    "ldap",
    "anydbm",
    "dbm",
    "gdbm",
    "sqlite3",
    "psycopg2",
    "mysql",
    "pymysql",
    "pymemcache",
    "redis",
    "memcache",
    "pickle",
    "marshal",
    "shelve",
    "anyio",
    "aiofiles",
    "pathlib",
    "glob",
    "fnmatch",
    "tempfile",
    "shutil",
    "tarfile",
    "zipfile",
    "fileinput",
    " ConfigParser",
    "configparser",
    "csv",
    "io",
    "builtins",
    "__builtin__",
    "imp",
    "importlib",
    "pkgutil",
    "zipimport",
    "sysconfig",
    "code",
    "codeop",
    "compile",
    "exec",
    "eval",
    "execfile",
    "input",
    "open",
    "file",
    "print",
    "exit",
    "quit",
    "help",
    "license",
    "credits",
    "dir",
    "vars",
    "type",
    "repr",
    "breakpoint",
    "display",
    " interactive",
    "interact",
    "enable_grep",
    "disable_grep",
    "enable_widget",
    "disable_widget",
}

# Blacklisted function names (even if imported from safe modules)
DANGEROUS_FUNCTIONS: Set[str] = {
    "system",
    "popen",
    "spawn",
    "fork",
    "forkpty",
    "execv",
    "execve",
    "spawnv",
    "spawnve",
    "load_module",
    "load_source",
    "compile",
    "eval",
    "exec",
    "execfile",
    "open",
    "file",
    "input",
    "raw_input",
    "breakpoint",
    "__import__",
    "reload",
}

# Blacklisted attribute accesses
DANGEROUS_ATTRIBUTES: Set[str] = {
    "os.system",
    "os.popen",
    "os.execl",
    "os.execv",
    "os.execve",
    "os.spawnv",
    "os.spawnve",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.exec",
    "subprocess.execute",
    "subprocess.shell",
    "socket.create_connection",
    "socket.socket",
    "socket.gethostbyname",
    "urllib.request.urlopen",
    "urllib.request.urlretrieve",
    "requests.get",
    "requests.post",
    "requests.request",
    "pickle.load",
    "pickle.loads",
    "pickle.dump",
    "pickle.dumps",
    "marshal.load",
    "marshal.loads",
    "__builtins__",
    "__globals__",
    "__locals__",
    "__code__",
    "__func__",
}


@dataclass
class ScanResult:
    """Result of a security scan."""

    safe: bool
    violations: List[Tuple[str, str]]  # List of (type, description)
    line_number: int
    code_snippet: str


class SecurityScanner:
    """AST-based security scanner for Python code."""

    def __init__(self, whitelist: List[str] | None = None):
        """Initialize the scanner.

        Args:
            whitelist: Optional list of patterns to allow despite blacklist
        """
        self.whitelist = whitelist or []

    def scan(self, code: str) -> ScanResult:
        """Scan code for security violations.

        Args:
            code: Python code to scan

        Returns:
            ScanResult with violations if any
        """
        violations: List[Tuple[str, str]] = []

        # Skip empty code
        if not code or not code.strip():
            return ScanResult(safe=True, violations=[], line_number=0, code_snippet="")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ScanResult(
                safe=False,
                violations=[("syntax_error", f"Syntax error: {e}")],
                line_number=e.lineno or 0,
                code_snippet=code,
            )

        # Walk the AST and check for violations
        for node in ast.walk(tree):
            violations.extend(self._check_node(node, code))

        # Check against whitelist
        violations = [v for v in violations if not self._is_whitelisted(v[1])]

        return ScanResult(
            safe=len(violations) == 0,
            violations=violations,
            line_number=0,  # Could track first violation line
            code_snippet=code,
        )

    def _check_node(self, node: ast.AST, code: str) -> List[Tuple[str, str]]:
        """Check a single AST node for violations.

        Args:
            node: AST node to check
            code: Original code for line number lookup

        Returns:
            List of (type, description) tuples
        """
        violations = []

        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.split(".")[0]
                if name in SYSTEM_MODULES:
                    violations.append(
                        ("import", f"Import of blacklisted module: {name}")
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module in SYSTEM_MODULES:
                    violations.append(
                        ("import", f"Import from blacklisted module: {module}")
                    )

        # Check attribute access
        elif isinstance(node, ast.Attribute):
            full_name = self._get_full_attribute_name(node)
            if full_name in DANGEROUS_ATTRIBUTES:
                violations.append(
                    ("attribute", f"Access to dangerous attribute: {full_name}")
                )

        # Check function calls
        elif isinstance(node, ast.Call):
            # Check for dangerous function calls
            if isinstance(node.func, ast.Name):
                if node.func.id in DANGEROUS_FUNCTIONS:
                    violations.append(
                        ("function", f"Call to dangerous function: {node.func.id}")
                    )
            elif isinstance(node.func, ast.Attribute):
                attr_name = self._get_full_attribute_name(node.func)
                if attr_name in DANGEROUS_ATTRIBUTES:
                    violations.append(
                        ("attribute", f"Call to dangerous attribute: {attr_name}")
                    )

        # Check for exec/eval
        elif isinstance(node, (ast.Exec, ast.Eval)):
            violations.append(("dangerous", "Use of exec() or eval() is not allowed"))

        # Check for open() calls on file objects
        elif isinstance(node, ast.NameConstant):
            # Check for True/False/None being assigned to dangerous names
            pass

        return violations

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full dotted name of an attribute access.

        Args:
            node: Attribute AST node

        Returns:
            Full name like "os.system"
        """
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    def _is_whitelisted(self, description: str) -> bool:
        """Check if a violation is whitelisted.

        Args:
            description: Violation description

        Returns:
            True if whitelisted, False otherwise
        """
        for pattern in self.whitelist:
            if pattern in description:
                return True
        return False


def quick_scan(code: str) -> bool:
    """Quick check if code appears safe (without detailed result).

    Args:
        code: Python code to check

    Returns:
        True if code appears safe, False if violations detected
    """
    scanner = SecurityScanner()
    result = scanner.scan(code)
    return result.safe
