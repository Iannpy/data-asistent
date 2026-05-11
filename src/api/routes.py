"""API routes for the data agent."""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from src.api.schemas import (
    ErrorResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    VisualizationRequest,
    VisualizationResponse,
)
from src.agent.core import AgentCore
from src.agent.session import SessionManager
from src.executor.kernel import KernelClient
from src.executor.sandbox import SandboxManager
from src.formatters.dataframe import format_dataframe
from src.formatters.scalar import format_scalar, is_scalar

# Initialize components
session_manager = SessionManager()
sandbox_manager = SandboxManager()
kernel_client: KernelClient | None = None

# Routers
router = APIRouter()


def get_kernel() -> KernelClient:
    """Get or create the kernel client singleton."""
    global kernel_client
    if kernel_client is None:
        kernel_client = KernelClient()
    return kernel_client


def get_agent() -> AgentCore:
    """Get the agent core instance."""
    return AgentCore(kernel_client=get_kernel(), session_manager=session_manager)


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Execute a natural language query",
    description="Translates a natural language query to Pandas code and executes it in the sandbox.",
)
async def query_endpoint(
    request: QueryRequest,
) -> QueryResponse:
    """Execute a natural language query against a dataset."""
    import time

    start_time = time.perf_counter()

    try:
        kernel = get_kernel()
        agent = get_agent()

        # Update session with dataset path
        session_manager.set_dataset_path(
            session_id=request.session_id or "default",
            dataset_path=request.dataset_path,
        )

        # Generate and execute code
        result = await agent.execute_query(
            query=request.query,
            dataset_path=request.dataset_path,
            session_id=request.session_id or "default",
        )

        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        return QueryResponse(
            success=result["success"],
            result=result.get("result"),
            error=result.get("error"),
            execution_time_ms=execution_time_ms,
            generated_code=result.get("generated_code"),
            session_id=request.session_id,
        )

    except Exception as e:
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        return QueryResponse(
            success=False,
            error=str(e),
            execution_time_ms=execution_time_ms,
            session_id=request.session_id,
        )


@router.post(
    "/visualize",
    response_model=VisualizationResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Generate a visualization",
    description="Generates a chart from a natural language description.",
)
async def visualize_endpoint(
    request: VisualizationRequest,
) -> VisualizationResponse:
    """Generate a visualization from a natural language query."""
    import time

    start_time = time.perf_counter()

    try:
        kernel = get_kernel()
        agent = get_agent()

        # Update session with dataset path
        session_manager.set_dataset_path(
            session_id=request.session_id or "default",
            dataset_path=request.dataset_path,
        )

        # Generate and execute visualization code
        result = await agent.execute_visualization(
            query=request.query,
            dataset_path=request.dataset_path,
            chart_type=request.chart_type,
            session_id=request.session_id or "default",
        )

        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        return VisualizationResponse(
            success=result["success"],
            image_base64=result.get("image_base64"),
            error=result.get("error"),
            execution_time_ms=execution_time_ms,
            chart_metadata=result.get("chart_metadata"),
            generated_code=result.get("generated_code"),
            session_id=request.session_id,
        )

    except Exception as e:
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        return VisualizationResponse(
            success=False,
            error=str(e),
            execution_time_ms=execution_time_ms,
            session_id=request.session_id,
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Check the health of the API and its dependencies.",
)
async def health_endpoint() -> HealthResponse:
    """Check the health of the API, kernel, and sandbox."""
    from datetime import datetime

    kernel_status = "ready"
    sandbox_status = "running"

    try:
        kernel = get_kernel()
        if not kernel.is_alive():
            kernel_status = "error"
    except Exception:
        kernel_status = "error"
        sandbox_status = "error"

    return HealthResponse(
        status="healthy" if kernel_status == "ready" else "unhealthy",
        kernel_status=kernel_status,
        sandbox_status=sandbox_status,
        timestamp=datetime.utcnow().isoformat(),
    )
