# API Documentation

## Overview

Neopilot provides two main API services:

1. **AI Gateway Service**: REST API for AI features
2. **Neoai Workflow Service**: gRPC API for workflow orchestration

## AI Gateway Service

### Base URL

```
http://localhost:8000/api
```

### API Versions

The AI Gateway supports multiple API versions:

- **v1**: Legacy API
- **v2**: Current stable API
- **v3**: Enhanced code suggestions
- **v4**: Latest features

### Authentication

All endpoints require authentication via GitLab tokens:

```http
Authorization: Bearer <gitlab-token>
```

### Endpoints

#### Code Completions

**POST** `/v2/code/completions`

Generate code completions based on context.

**Request:**
```json
{
  "prompt": "def calculate_fibonacci(",
  "language": "python",
  "max_tokens": 100,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "choices": [
    {
      "text": "n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
      "finish_reason": "stop"
    }
  ],
  "model": "claude-3-5-sonnet",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 45,
    "total_tokens": 55
  }
}
```

#### Code Generations

**POST** `/v2/code/generations`

Generate complete code blocks from natural language.

**Request:**
```json
{
  "prompt": "Create a function to validate email addresses",
  "language": "python",
  "context": {
    "file_path": "validators.py",
    "imports": ["re"]
  }
}
```

**Response:**
```json
{
  "code": "import re\n\ndef validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "explanation": "This function uses regex to validate email format"
}
```

#### Chat

**POST** `/v2/chat/agent`

Interact with conversational AI agent.

**Request:**
```json
{
  "message": "How do I implement authentication in FastAPI?",
  "conversation_id": "uuid-here",
  "context": {
    "project_type": "fastapi",
    "files": ["main.py", "auth.py"]
  }
}
```

**Response:**
```json
{
  "response": "To implement authentication in FastAPI, you can use OAuth2 with JWT tokens...",
  "suggestions": [
    "Install python-jose and passlib",
    "Create authentication endpoints",
    "Add security dependencies"
  ],
  "conversation_id": "uuid-here"
}
```

#### Prompts

**POST** `/v2/prompts/invoke`

Execute a registered prompt template.

**Request:**
```json
{
  "prompt_id": "code_review",
  "variables": {
    "code": "def foo():\n    pass",
    "language": "python"
  }
}
```

**Response:**
```json
{
  "result": "Code review results...",
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 150
  }
}
```

### Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid prompt format",
    "details": {
      "field": "prompt",
      "issue": "Cannot be empty"
    }
  }
}
```

**Error Codes:**
- `INVALID_REQUEST`: Malformed request
- `UNAUTHORIZED`: Authentication failed
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `RATE_LIMITED`: Too many requests
- `INTERNAL_ERROR`: Server error

## Neoai Workflow Service

### Protocol

gRPC with Protocol Buffers

### Service Definition

```protobuf
service WorkflowService {
  rpc ExecuteWorkflow(WorkflowRequest) returns (stream WorkflowResponse);
  rpc GetWorkflowStatus(StatusRequest) returns (StatusResponse);
  rpc CancelWorkflow(CancelRequest) returns (CancelResponse);
}
```

### Methods

#### ExecuteWorkflow

Execute a workflow with streaming responses.

**Request:**
```protobuf
message WorkflowRequest {
  string workflow_id = 1;
  string workflow_type = 2;  // "chat", "code_generation", etc.
  map<string, string> parameters = 3;
  string user_id = 4;
  string project_id = 5;
}
```

**Response Stream:**
```protobuf
message WorkflowResponse {
  string workflow_id = 1;
  string status = 2;  // "running", "completed", "failed"
  oneof payload {
    WorkflowMessage message = 3;
    WorkflowResult result = 4;
    WorkflowError error = 5;
  }
}
```

#### GetWorkflowStatus

Check the status of a running workflow.

**Request:**
```protobuf
message StatusRequest {
  string workflow_id = 1;
}
```

**Response:**
```protobuf
message StatusResponse {
  string workflow_id = 1;
  string status = 2;
  int32 progress_percentage = 3;
  repeated string completed_steps = 4;
  string current_step = 5;
}
```

#### CancelWorkflow

Cancel a running workflow.

**Request:**
```protobuf
message CancelRequest {
  string workflow_id = 1;
  string reason = 2;
}
```

**Response:**
```protobuf
message CancelResponse {
  bool success = 1;
  string message = 2;
}
```

### Client Example (Python)

```python
import grpc
from neopilot.contract import contract_pb2, contract_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')
stub = contract_pb2_grpc.WorkflowServiceStub(channel)

# Execute workflow
request = contract_pb2.WorkflowRequest(
    workflow_id="unique-id",
    workflow_type="chat",
    parameters={"message": "Hello"},
    user_id="user-123",
    project_id="project-456"
)

# Stream responses
for response in stub.ExecuteWorkflow(request):
    print(f"Status: {response.status}")
    if response.HasField('message'):
        print(f"Message: {response.message.content}")
    elif response.HasField('result'):
        print(f"Result: {response.result.data}")
```

### Client Example (Ruby)

```ruby
require 'gitlab/neoai_workflow_service'

# Create client
client = Gitlab::NeoaiWorkflowService::Client.new(
  host: 'localhost',
  port: 50051
)

# Execute workflow
request = Gitlab::NeoaiWorkflowService::WorkflowRequest.new(
  workflow_id: 'unique-id',
  workflow_type: 'chat',
  parameters: { 'message' => 'Hello' },
  user_id: 'user-123',
  project_id: 'project-456'
)

# Stream responses
client.execute_workflow(request) do |response|
  puts "Status: #{response.status}"
  case response.payload
  when :message
    puts "Message: #{response.message.content}"
  when :result
    puts "Result: #{response.result.data}"
  end
end
```

## Rate Limiting

### Limits

- **AI Gateway**: 100 requests/minute per user
- **Workflow Service**: 10 concurrent workflows per user

### Headers

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## Monitoring

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "version": "0.0.2",
  "services": {
    "ai_gateway": "up",
    "workflow_service": "up",
    "database": "up"
  }
}
```

### Metrics

Prometheus metrics available at `/metrics`:

- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request duration
- `workflow_executions_total`: Total workflow executions
- `workflow_duration_seconds`: Workflow execution time
- `llm_tokens_used_total`: Total tokens consumed

## Webhooks

### Workflow Events

Subscribe to workflow events:

**POST** `/webhooks/subscribe`

```json
{
  "url": "https://your-server.com/webhook",
  "events": ["workflow.completed", "workflow.failed"],
  "secret": "webhook-secret"
}
```

**Webhook Payload:**
```json
{
  "event": "workflow.completed",
  "workflow_id": "uuid",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "status": "completed",
    "result": {...}
  },
  "signature": "sha256=..."
}
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
try:
    response = client.execute_workflow(request)
except grpc.RpcError as e:
    if e.code() == grpc.StatusCode.UNAVAILABLE:
        # Retry logic
        pass
    elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
        # Fix request
        pass
```

### 2. Streaming

Use streaming for long-running operations:

```python
for response in stub.ExecuteWorkflow(request):
    # Process each response as it arrives
    update_ui(response)
```

### 3. Timeouts

Set appropriate timeouts:

```python
response = stub.ExecuteWorkflow(
    request,
    timeout=300  # 5 minutes
)
```

### 4. Retries

Implement exponential backoff:

```python
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=4, max=10))
def call_api():
    return client.execute_workflow(request)
```

## Support

For API support:
- Check [ARCHITECTURE.md](../ARCHITECTURE.md) for design details
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development
- Open an issue on GitHub
