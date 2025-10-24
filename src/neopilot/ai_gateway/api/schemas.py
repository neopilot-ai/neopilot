"""Pydantic schemas for OpenAPI documentation."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(str, Enum):
    """Standard error codes."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorDetail(BaseModel):
    """Error detail information."""

    field: Optional[str] = Field(None, description="Field that caused the error")
    issue: str = Field(..., description="Description of the issue")


class ErrorResponse(BaseModel):
    """Standard error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Invalid request parameters",
                    "details": {"field": "prompt", "issue": "Cannot be empty"},
                }
            }
        }
    )

    class Error(BaseModel):
        code: ErrorCode = Field(..., description="Error code")
        message: str = Field(..., description="Human-readable error message")
        details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    error: Error


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceStatus(BaseModel):
    """Individual service status."""

    status: HealthStatus = Field(..., description="Service health status")
    latency_ms: Optional[float] = Field(None, description="Service latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Health check response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "0.0.2",
                "services": {
                    "ai_gateway": {"status": "healthy", "latency_ms": 5.2},
                    "workflow_service": {"status": "healthy", "latency_ms": 8.1},
                    "database": {"status": "healthy", "latency_ms": 2.3},
                    "redis": {"status": "healthy", "latency_ms": 1.1},
                },
            }
        }
    )

    status: HealthStatus = Field(..., description="Overall system health")
    version: str = Field(..., description="API version")
    services: Dict[str, ServiceStatus] = Field(..., description="Individual service statuses")


class CodeCompletionRequest(BaseModel):
    """Request for code completion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "def calculate_fibonacci(",
                "language": "python",
                "max_tokens": 100,
                "temperature": 0.7,
                "context": {"file_path": "utils.py", "cursor_position": 42},
            }
        }
    )

    prompt: str = Field(..., description="Code context/prefix for completion", min_length=1)
    language: str = Field(..., description="Programming language", examples=["python", "javascript", "go"])
    max_tokens: int = Field(100, description="Maximum tokens to generate", ge=1, le=2000)
    temperature: float = Field(0.7, description="Sampling temperature", ge=0.0, le=2.0)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")


class CodeChoice(BaseModel):
    """Code completion choice."""

    text: str = Field(..., description="Generated code")
    finish_reason: str = Field(..., description="Reason completion finished", examples=["stop", "length"])
    index: int = Field(0, description="Choice index")


class TokenUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(..., description="Tokens in prompt")
    completion_tokens: int = Field(..., description="Tokens in completion")
    total_tokens: int = Field(..., description="Total tokens used")


class CodeCompletionResponse(BaseModel):
    """Response for code completion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "choices": [
                    {
                        "text": "n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
                        "finish_reason": "stop",
                        "index": 0,
                    }
                ],
                "model": "claude-3-5-sonnet",
                "usage": {"prompt_tokens": 10, "completion_tokens": 45, "total_tokens": 55},
            }
        }
    )

    choices: List[CodeChoice] = Field(..., description="Completion choices")
    model: str = Field(..., description="Model used for completion")
    usage: TokenUsage = Field(..., description="Token usage statistics")


class ChatMessage(BaseModel):
    """Chat message."""

    role: str = Field(..., description="Message role", examples=["user", "assistant", "system"])
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request for chat completion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "How do I implement authentication in FastAPI?",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "context": {"project_type": "fastapi", "files": ["main.py", "auth.py"]},
            }
        }
    )

    message: str = Field(..., description="User message", min_length=1)
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_tokens: int = Field(500, description="Maximum response tokens", ge=1, le=4000)
    temperature: float = Field(0.7, description="Sampling temperature", ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    """Response for chat completion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "To implement authentication in FastAPI, you can use OAuth2 with JWT tokens...",
                "suggestions": [
                    "Install python-jose and passlib",
                    "Create authentication endpoints",
                    "Add security dependencies",
                ],
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )

    response: str = Field(..., description="Assistant response")
    suggestions: Optional[List[str]] = Field(None, description="Follow-up suggestions")
    conversation_id: str = Field(..., description="Conversation ID")
    usage: Optional[TokenUsage] = Field(None, description="Token usage")


class ModelInfo(BaseModel):
    """LLM model information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "claude-3-5-sonnet",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
                "max_tokens": 200000,
                "capabilities": ["code", "chat", "analysis"],
            }
        }
    )

    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Human-readable model name")
    provider: str = Field(..., description="Model provider", examples=["openai", "anthropic", "vertex_ai"])
    max_tokens: int = Field(..., description="Maximum context tokens")
    capabilities: List[str] = Field(..., description="Model capabilities")


class ModelsResponse(BaseModel):
    """List of available models."""

    models: List[ModelInfo] = Field(..., description="Available models")
