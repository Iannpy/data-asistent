"""LLM provider interface using strategy pattern.

This module provides the Agent Core with a pluggable LLM provider interface.
Supports Ollama (default), OpenAI, and Anthropic providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings


# =============================================================================
# Provider Interface (Strategy Pattern)
# =============================================================================


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        raise NotImplementedError


@dataclass
class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    base_url: str = field(default_factory=lambda: settings.ollama_base_url)
    model: str = field(default_factory=lambda: settings.llm_model)
    timeout: int = 120

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate code using Ollama API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": kwargs.get("model", self.model),
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.1),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


@dataclass
class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    api_key: str = field(default_factory=lambda: settings.openai_api_key or "")
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 120

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate code using OpenAI API."""
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": kwargs.get("temperature", 0.1),
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


@dataclass
class AnthropicProvider(LLMProvider):
    """Anthropic API provider."""

    api_key: str = field(default_factory=lambda: settings.anthropic_api_key or "")
    model: str = "claude-3-haiku-20240307"
    base_url: str = "https://api.anthropic.com/v1"
    timeout: int = 120

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate code using Anthropic API."""
        if not self.api_key:
            raise ValueError("Anthropic API key not configured")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


# =============================================================================
# Provider Factory
# =============================================================================


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: Dict[str, type] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def create(cls, provider_name: Optional[str] = None) -> LLMProvider:
        """Create an LLM provider instance based on configuration."""
        name = provider_name or settings.llm_provider
        provider_class = cls._providers.get(name.lower())

        if not provider_class:
            raise ValueError(
                f"Unknown LLM provider: {name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        return provider_class()

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        """Register a custom LLM provider."""
        cls._providers[name.lower()] = provider_class


# =============================================================================
# Prompt Templates
# =============================================================================


QUERY_PROMPT_TEMPLATE = """You are a data analysis assistant. Generate Python Pandas code to answer the user's question.

Dataset path: {dataset_path}

IMPORTANT RULES:
1. Use pandas to load and analyze the data from `{dataset_path}`
2. The dataframe is already loaded as `df`
3. Return ONLY the Python code, no explanations
4. Keep the code simple and focused on the requested analysis
5. Do NOT use print() statements - return results as variables
6. Do NOT access the filesystem beyond reading the dataset

User question: {query}

Generated code:"""

AMBIGUOUS_QUERY_PROMPT = """The user's query is ambiguous: "{query}"

Please ask a clarifying question to gather the necessary information.
Only ask ONE question at a time.
Focus on the most important missing information.

Response format:
CLARIFICATION: [your question]"""

VISUALIZATION_PROMPT_TEMPLATE = """You are a data visualization assistant. Generate Python matplotlib/seaborn/plotly code to create a chart.

Dataset path: {dataset_path}

IMPORTANT RULES:
1. Use pandas to load the data from `{dataset_path}`
2. The dataframe is loaded as `df`
3. Generate a {chart_type} chart
4. Return ONLY the Python code, no explanations
5. Use matplotlib inline backend: `%matplotlib inline`
6. Save the figure to a BytesIO buffer as PNG: `buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=100); buf.seek(0)`
7. Encode the buffer as base64: `import base64; base64.b64encode(buf.getvalue()).decode('utf-8')`
8. Assign the base64 string to a variable called `image_base64`

User request: {query}

Generated code:"""

ERROR_CONTEXT_PROMPT = """The previous code execution failed with the following error:
{error}

Original query: {query}

Please generate corrected Python Pandas code that fixes the error.
Return ONLY the corrected code."""

SESSION_CONTEXT_PROMPT = """Previous conversation history:
{history}

Current query: {query}

Generate code that takes the conversation context into account."""


# =============================================================================
# Agent Core
# =============================================================================


@dataclass
class AgentResult:
    """Result from the agent's code generation."""

    code: str
    success: bool
    error: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


class AgentCore:
    """Core agent that translates natural language to executable code."""

    def __init__(
        self,
        kernel_client: Any = None,
        session_manager: Any = None,
        provider: Optional[LLMProvider] = None,
    ):
        """Initialize the agent core.

        Args:
            kernel_client: Jupyter kernel client for code execution
            session_manager: Session manager for context
            provider: LLM provider instance (auto-created if None)
        """
        self.kernel = kernel_client
        self.session_manager = session_manager
        self.provider = provider or LLMProviderFactory.create()
        self._code_history: Dict[str, List[str]] = {}

    async def generate_code(
        self,
        query: str,
        dataset_path: str,
        session_id: str = "default",
    ) -> AgentResult:
        """Generate Python code from a natural language query.

        Args:
            query: Natural language query
            dataset_path: Path to the dataset
            session_id: Session identifier

        Returns:
            AgentResult with generated code or clarification request
        """
        # Build prompt with context
        context = ""
        if session_id in self._code_history and self._code_history[session_id]:
            history = self._code_history[session_id][-3:]  # Last 3 exchanges
            context = SESSION_CONTEXT_PROMPT.format(
                query=query,
                history="\n".join(history),
            )
        else:
            context = query

        prompt = QUERY_PROMPT_TEMPLATE.format(
            query=context,
            dataset_path=dataset_path,
        )

        try:
            response = await self.provider.generate(prompt)

            # Check if response indicates ambiguous query
            if response.strip().startswith("CLARIFICATION:"):
                return AgentResult(
                    code="",
                    success=False,
                    needs_clarification=True,
                    clarification_question=response.replace("CLARIFICATION:", "").strip(),
                )

            return AgentResult(code=response.strip(), success=True)

        except Exception as e:
            return AgentResult(
                code="",
                success=False,
                error=f"LLM generation failed: {str(e)}",
            )

    async def generate_visualization(
        self,
        query: str,
        dataset_path: str,
        chart_type: Optional[str] = None,
        session_id: str = "default",
    ) -> AgentResult:
        """Generate visualization code from a natural language query.

        Args:
            query: Natural language description
            dataset_path: Path to the dataset
            chart_type: Desired chart type (histogram, scatter, etc.)
            session_id: Session identifier

        Returns:
            AgentResult with generated code
        """
        chart = chart_type or "appropriate"

        prompt = VISUALIZATION_PROMPT_TEMPLATE.format(
            query=query,
            dataset_path=dataset_path,
            chart_type=chart,
        )

        try:
            response = await self.provider.generate(prompt)
            return AgentResult(code=response.strip(), success=True)
        except Exception as e:
            return AgentResult(
                code="",
                success=False,
                error=f"Visualization generation failed: {str(e)}",
            )

    async def regenerate_with_context(
        self,
        query: str,
        dataset_path: str,
        error: str,
        session_id: str = "default",
    ) -> AgentResult:
        """Regenerate code after a failed execution.

        Args:
            query: Original query
            dataset_path: Path to the dataset
            error: Error message from failed execution
            session_id: Session identifier

        Returns:
            AgentResult with corrected code
        """
        prompt = ERROR_CONTEXT_PROMPT.format(
            query=query,
            error=error,
        )

        try:
            response = await self.provider.generate(prompt)
            return AgentResult(code=response.strip(), success=True)
        except Exception as e:
            return AgentResult(
                code="",
                success=False,
                error=f"Regeneration failed: {str(e)}",
            )

    def record_code(self, session_id: str, code: str) -> None:
        """Record generated code for session context.

        Args:
            session_id: Session identifier
            code: Generated code
        """
        if session_id not in self._code_history:
            self._code_history[session_id] = []
        self._code_history[session_id].append(code)
        # Keep only last 10 exchanges
        self._code_history[session_id] = self._code_history[session_id][-10:]

    async def execute_query(
        self,
        query: str,
        dataset_path: str,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Execute a query end-to-end: generate code and run it.

        Args:
            query: Natural language query
            dataset_path: Path to the dataset
            session_id: Session identifier

        Returns:
            Dict with success, result/error, generated_code
        """
        from src.executor.security import SecurityScanner

        scanner = SecurityScanner()

        # Generate code
        result = await self.generate_code(query, dataset_path, session_id)

        if result.needs_clarification:
            return {
                "success": False,
                "error": result.clarification_question,
                "generated_code": None,
            }

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "generated_code": None,
            }

        # Security scan
        scan_result = scanner.scan(result.code)
        if not scan_result.safe:
            return {
                "success": False,
                "error": f"Security violation: {scan_result.violations}",
                "generated_code": result.code,
            }

        # Execute in kernel
        try:
            exec_result = await self.kernel.execute(result.code)

            if exec_result.stderr and "Error" in exec_result.stderr:
                # Try to regenerate with error context
                regen_result = await self.regenerate_with_context(
                    query, dataset_path, exec_result.stderr, session_id
                )
                if regen_result.success:
                    # Scan regenerated code
                    regen_scan = scanner.scan(regen_result.code)
                    if not regen_scan.safe:
                        return {
                            "success": False,
                            "error": f"Security violation in regenerated code: {regen_scan.violations}",
                            "generated_code": regen_result.code,
                        }
                    exec_result = await self.kernel.execute(regen_result.code)
                    self.record_code(session_id, regen_result.code)
                else:
                    return {
                        "success": False,
                        "error": exec_result.stderr,
                        "generated_code": result.code,
                    }
            else:
                self.record_code(session_id, result.code)

            # Format result
            if is_scalar(exec_result.result):
                formatted = format_scalar(exec_result.result)
            else:
                formatted = format_dataframe(exec_result.result)

            return {
                "success": True,
                "result": formatted,
                "generated_code": result.code,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "generated_code": result.code,
            }

    async def execute_visualization(
        self,
        query: str,
        dataset_path: str,
        chart_type: Optional[str] = None,
        session_id: str = "default",
    ) -> Dict[str, Any]:
        """Execute a visualization end-to-end.

        Args:
            query: Natural language description
            dataset_path: Path to the dataset
            chart_type: Desired chart type
            session_id: Session identifier

        Returns:
            Dict with success, image_base64, chart_metadata, generated_code
        """
        from src.executor.security import SecurityScanner

        scanner = SecurityScanner()

        # Generate code
        result = await self.generate_visualization(
            query, dataset_path, chart_type, session_id
        )

        if not result.success:
            return {
                "success": False,
                "error": result.error,
                "image_base64": None,
                "generated_code": None,
            }

        # Security scan
        scan_result = scanner.scan(result.code)
        if not scan_result.safe:
            return {
                "success": False,
                "error": f"Security violation: {scan_result.violations}",
                "image_base64": None,
                "generated_code": result.code,
            }

        # Execute in kernel
        try:
            exec_result = await self.kernel.execute(result.code)
            self.record_code(session_id, result.code)

            # Extract base64 image from result
            image_base64 = None
            chart_metadata = {}

            if hasattr(exec_result, "result") and exec_result.result:
                result_str = str(exec_result.result)
                if "image_base64" in result_str:
                    # The image should be in the result - extract it
                    # In real implementation, parse the kernel output
                    image_base64 = extract_base64_from_result(exec_result)

            return {
                "success": True,
                "image_base64": image_base64,
                "chart_metadata": chart_metadata,
                "generated_code": result.code,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_base64": None,
                "generated_code": result.code,
            }


def extract_base64_from_result(exec_result: Any) -> Optional[str]:
    """Extract base64 image string from kernel execution result.

    Args:
        exec_result: ExecutionResult from kernel

    Returns:
        Base64 string or None
    """
    # Try to extract from various result formats
    if hasattr(exec_result, "result"):
        result = exec_result.result
        if isinstance(result, dict) and "image_base64" in result:
            return result["image_base64"]
        if isinstance(result, str):
            return result
    return None
