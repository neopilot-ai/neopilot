# Contributing to Neopilot

Thank you for your interest in contributing to Neopilot! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Git

### Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/neopilot.git
cd neopilot

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --extra test

# Activate virtual environment
source .venv/bin/activate

# Install pre-commit hooks
uv run pre-commit install
```

## Development Workflow

### 1. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or a bugfix branch
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, maintainable code
- Follow the coding standards below
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov --cov-report=html

# Run specific test file
uv run pytest tests/test_methods.py

# Run integration tests
uv run pytest -m integration
```

### 4. Format and Lint

```bash
# Format code with Black
uv run black src/ tests/

# Run Flake8
uv run flake8 src/ tests/

# Run Pylint
uv run pylint src/

# Run Bandit security checks
uv run bandit -r src/

# Run all pre-commit hooks
uv run pre-commit run --all-files
```

### 5. Commit Changes

```bash
git add .
git commit -m "type: description"
```

See [Commit Messages](#commit-messages) for guidelines.

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line Length**: 120 characters (configured in pyproject.toml)
- **Formatter**: Black (automatic formatting)
- **Import Order**: Use isort or follow PEP 8 import ordering
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

### Example

```python
from typing import Optional, List

def process_workflow(
    workflow_id: str,
    steps: List[str],
    timeout: Optional[int] = None
) -> dict:
    """Process a workflow with the given steps.
    
    Args:
        workflow_id: Unique identifier for the workflow
        steps: List of workflow steps to execute
        timeout: Optional timeout in seconds
        
    Returns:
        Dictionary containing workflow results
        
    Raises:
        ValueError: If workflow_id is invalid
        TimeoutError: If workflow exceeds timeout
    """
    # Implementation here
    pass
```

### Code Organization

- **Modules**: One class per file (when possible)
- **Imports**: Group by standard library, third-party, local
- **Constants**: UPPER_CASE at module level
- **Classes**: PascalCase
- **Functions/Variables**: snake_case
- **Private**: Prefix with underscore `_`

### Error Handling

```python
# Good: Specific exceptions
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise

# Bad: Bare except
try:
    result = risky_operation()
except:
    pass
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                  # Unit tests
├── integration/           # Integration tests
└── conftest.py           # Pytest fixtures
```

### Writing Tests

```python
import pytest
from neopilot.module import function_to_test

class TestFunctionName:
    """Test suite for function_to_test."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        result = function_to_test("input")
        assert result == "expected"
    
    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            function_to_test(None)
    
    @pytest.mark.integration
    def test_integration(self):
        """Test integration with external service."""
        # Integration test code
        pass
```

### Test Coverage

- Aim for **100% coverage** for new code
- Minimum **80% coverage** for modified code
- Use `pytest --cov` to check coverage
- Add tests before fixing bugs (TDD approach)

### Test Markers

```python
@pytest.mark.unit          # Fast, isolated tests
@pytest.mark.integration   # Tests with external dependencies
@pytest.mark.slow          # Long-running tests
@pytest.mark.gpu           # Tests requiring GPU
@pytest.mark.spark         # Tests requiring Spark
```

## Commit Messages

### Format

```
type(scope): subject

body (optional)

footer (optional)
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **ci**: CI/CD changes

### Examples

```
feat(ai-gateway): add support for Claude 3.5 Sonnet

Implement integration with Anthropic's Claude 3.5 Sonnet model
including prompt formatting and response parsing.

Closes #123
```

```
fix(workflow): resolve race condition in checkpointer

The checkpointer was not properly handling concurrent writes.
Added mutex lock to prevent data corruption.

Fixes #456
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Coverage meets requirements
- [ ] Documentation updated
- [ ] Pre-commit hooks pass
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with main

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

### Review Process

1. **Automated Checks**: CI/CD must pass
2. **Code Review**: At least one approval required
3. **Testing**: All tests must pass
4. **Documentation**: Must be updated if needed
5. **Merge**: Squash and merge to main

## Project-Specific Guidelines

### AI Gateway Service

- Follow FastAPI best practices
- Use dependency injection via containers
- Add proper error handling and logging
- Include OpenAPI documentation

### Neoai Workflow Service

- Use LangChain/LangGraph patterns
- Implement proper state management
- Add comprehensive tool documentation
- Include workflow diagrams for complex flows

### Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Validate all user inputs
- Follow OWASP guidelines

### Performance

- Profile code for bottlenecks
- Use async/await for I/O operations
- Implement caching where appropriate
- Monitor memory usage

## Getting Help

- **Documentation**: Check [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: Search existing issues or create new one
- **Discussions**: Use GitHub Discussions for questions
- **Support**: See [SUPPORT.md](SUPPORT.md)

## Recognition

Contributors will be recognized in:
- GitHub contributors page
- Release notes
- Project documentation

Thank you for contributing to Neopilot! 🚀
