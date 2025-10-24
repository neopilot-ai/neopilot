"""OpenAPI/Swagger configuration for AI Gateway API."""

from typing import Any, Dict

# OpenAPI metadata
OPENAPI_METADATA = {
    "title": "Neopilot AI Gateway API",
    "description": """
# Neopilot AI Gateway API

AI-powered code assistance and workflow automation platform.

## Features

- 🤖 **Code Completions**: Intelligent code completion and suggestions
- 💬 **Chat Interface**: Conversational AI for development assistance
- 🔄 **Workflow Automation**: Orchestrate complex AI-powered workflows
- 🔌 **Multi-Provider**: Support for OpenAI, Anthropic, Vertex AI, and more

## Authentication

All endpoints require authentication via GitLab token:

```
Authorization: Bearer <gitlab-token>
```

## Rate Limiting

- **Default**: 100 requests per minute per user
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Versioning

The API supports multiple versions (v1, v2, v3, v4). Use the version prefix in your requests:

- `/api/v1/...` - Legacy API
- `/api/v2/...` - Current stable API
- `/api/v3/...` - Enhanced features
- `/api/v4/...` - Latest features

## Support

- Documentation: https://github.com/khulnasoft/neopilot
- Issues: https://github.com/khulnasoft/neopilot/issues
    """,
    "version": "0.0.2",
    "contact": {
        "name": "KhulnaSoft DevOps",
        "email": "info@khulnasoft.com",
        "url": "https://github.com/khulnasoft/neopilot",
    },
    "license_info": {"name": "MIT License", "url": "https://github.com/khulnasoft/neopilot/blob/main/LICENSE"},
    "terms_of_service": "https://github.com/khulnasoft/neopilot/blob/main/CODE_OF_CONDUCT.md",
}

# API Tags for grouping endpoints
TAGS_METADATA = [
    {"name": "health", "description": "Health check and system status endpoints"},
    {"name": "code-completions", "description": "Code completion and suggestion endpoints"},
    {"name": "code-generations", "description": "Code generation from natural language"},
    {"name": "chat", "description": "Conversational AI interface"},
    {"name": "prompts", "description": "Prompt template management and execution"},
    {"name": "workflows", "description": "Workflow orchestration and management"},
    {"name": "models", "description": "LLM model information and configuration"},
    {"name": "admin", "description": "Administrative endpoints (requires admin privileges)"},
]

# Security schemes
SECURITY_SCHEMES = {
    "GitLabToken": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "GitLab Personal Access Token",
        "description": "GitLab Personal Access Token for authentication",
    },
    "APIKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API Key for service-to-service authentication",
    },
}

# Common response models
COMMON_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request parameters",
                        "details": {"field": "prompt", "issue": "Cannot be empty"},
                    }
                }
            }
        },
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {"example": {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}}
        },
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {"example": {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}}}
        },
    },
    404: {
        "description": "Not Found",
        "content": {"application/json": {"example": {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}}},
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded. Retry after 60 seconds."}
                }
            }
        },
        "headers": {
            "Retry-After": {"description": "Seconds to wait before retrying", "schema": {"type": "integer"}},
            "X-RateLimit-Limit": {"description": "Request limit per window", "schema": {"type": "integer"}},
            "X-RateLimit-Remaining": {"description": "Remaining requests in window", "schema": {"type": "integer"}},
            "X-RateLimit-Reset": {"description": "Unix timestamp when limit resets", "schema": {"type": "integer"}},
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}
            }
        },
    },
    503: {
        "description": "Service Unavailable",
        "content": {
            "application/json": {
                "example": {"error": {"code": "SERVICE_UNAVAILABLE", "message": "Service temporarily unavailable"}}
            }
        },
    },
}

# Servers configuration
SERVERS = [
    {"url": "http://localhost:8000", "description": "Local development server"},
    {"url": "https://api-staging.neopilot.example.com", "description": "Staging environment"},
    {"url": "https://api.neopilot.example.com", "description": "Production environment"},
]


def get_openapi_config() -> dict:
    """Get complete OpenAPI configuration."""
    return {
        **OPENAPI_METADATA,
        "openapi_tags": TAGS_METADATA,
        "servers": SERVERS,
        "components": {"securitySchemes": SECURITY_SCHEMES},
        "security": [{"GitLabToken": []}],
    }
