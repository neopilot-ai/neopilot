# Linting Guide

## Overview

This project uses multiple linting tools to ensure code quality and consistency.

## Tools

### 1. Black (Code Formatter)
- **Purpose**: Automatic code formatting
- **Line Length**: 120 characters
- **Config**: `pyproject.toml` → `[tool.black]`

### 2. Flake8 (Style Guide Enforcement)
- **Purpose**: PEP 8 compliance
- **Config**: `.flake8`
- **Max Line Length**: 120 characters

### 3. Pylint (Code Analysis)
- **Purpose**: Code quality and error detection
- **Config**: `pyproject.toml` → `[tool.pylint]`

### 4. Bandit (Security Linter)
- **Purpose**: Security vulnerability detection
- **Config**: `pyproject.toml` → `[tool.bandit]`

## Quick Commands

```bash
# Auto-format code
make format

# Auto-fix common issues
make format-fix

# Run all linters
make lint

# Run security checks
make security

# Run all checks
make check
```

## Common Issues & Fixes

### E501: Line too long

**Automatic Fix**: Run `make format`

**Manual Fix**: Break long lines:
```python
# Bad
some_very_long_function_call_with_many_parameters(param1, param2, param3, param4, param5, param6)

# Good
some_very_long_function_call_with_many_parameters(
    param1,
    param2,
    param3,
    param4,
    param5,
    param6,
)
```

### E704: Multiple statements on one line (def)

**Issue**: Function definition and body on same line

```python
# Bad
def function(): ...

# Good
def function():
    ...
```

**Fix**: Move ellipsis or pass to new line

### B006: Mutable default arguments

**Issue**: Using mutable objects as default arguments

```python
# Bad
def function(items=[]):
    items.append(1)
    return items

# Good
def function(items=None):
    if items is None:
        items = []
    items.append(1)
    return items
```

**Why**: Default arguments are created once at function definition time, not at call time.

### B903: Data class should use __slots__

**Issue**: Data classes without `__slots__` use more memory

```python
# Bad
@dataclass
class MyData:
    value: int

# Good
@dataclass
class MyData:
    __slots__ = ['value']
    value: int

# Or use frozen
@dataclass(frozen=True)
class MyData:
    value: int
```

### B036: Don't except BaseException

**Issue**: Catching `BaseException` catches system exits

```python
# Bad
try:
    risky_operation()
except BaseException:
    handle_error()

# Good
try:
    risky_operation()
except Exception as e:
    handle_error(e)

# Or if you must catch BaseException, re-raise
try:
    risky_operation()
except BaseException:
    cleanup()
    raise
```

### B007: Loop control variable not used

**Issue**: Loop variable declared but not used

```python
# Bad
for key in dictionary:
    do_something()

# Good
for _ in dictionary:
    do_something()

# Or if you need the count
for _key in dictionary:
    do_something()
```

### B010: setattr with constant

**Issue**: Using `setattr` with a constant attribute name

```python
# Bad
setattr(obj, "attribute", value)

# Good
obj.attribute = value
```

**Exception**: When the attribute name is dynamic, `setattr` is appropriate.

### B039: ContextVar with mutable default

**Issue**: ContextVar with mutable default value

```python
# Bad
from contextvars import ContextVar
my_var = ContextVar("my_var", default=[])

# Good
from contextvars import ContextVar
my_var = ContextVar("my_var", default=None)

def get_my_list():
    value = my_var.get()
    if value is None:
        value = []
        my_var.set(value)
    return value
```

### F401: Imported but unused

**Issue**: Import statement not used

```python
# Bad
from typing import List, Dict
def function() -> Dict:
    return {}

# Good
from typing import Dict
def function() -> Dict:
    return {}
```

**Auto-fix**: Most IDEs can remove unused imports automatically.

## Configuration Files

### .flake8

```ini
[flake8]
max-line-length = 120
extend-ignore = E203, W503, E501
exclude = .git, __pycache__, build, dist
```

### pyproject.toml

```toml
[tool.black]
line-length = 120
fast = true

[tool.bandit]
exclude_dirs = ["build","dist","tests","scripts"]
skips = ["B006", "B008", "B010", "B036", "B039", "B903"]

[tool.pylint.messages_control]
max-line-length = 120
disable = [
    "C0103",  # Invalid name
    "C0114",  # Missing module docstring
    "R0913",  # Too many arguments
]
```

## Ignored Warnings

Some warnings are intentionally ignored because they represent valid patterns in this codebase:

- **B006**: Mutable defaults are used intentionally in some APIs
- **B008**: Function calls in argument defaults (FastAPI dependencies)
- **B010**: `setattr` used for dynamic attribute setting
- **B036**: `BaseException` caught in cleanup code with re-raise
- **B039**: ContextVar patterns that are safe
- **B903**: Data classes without slots (performance not critical)

## Pre-commit Hooks

Install pre-commit hooks to run linters automatically:

```bash
make install-dev
```

This will run formatters and linters before each commit.

## CI/CD Integration

Linting runs automatically in CI/CD:

```yaml
# .github/workflows/build-and-test.yml
- name: Run Black
  run: uv run black --check src/ tests/

- name: Run Flake8
  run: uv run flake8 src/ tests/

- name: Run Pylint
  run: uv run pylint src/

- name: Run Bandit
  run: uv run bandit -r src/
```

## Best Practices

### 1. Format Before Committing
```bash
make format
git add .
git commit -m "your message"
```

### 2. Fix Issues Incrementally
Don't try to fix all linting issues at once. Fix them file by file:

```bash
# Fix specific file
uv run black src/neopilot/specific_file.py
uv run flake8 src/neopilot/specific_file.py
```

### 3. Use Type Hints
```python
# Good
def process_data(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}
```

### 4. Write Docstrings
```python
def complex_function(param1: str, param2: int) -> bool:
    """Process data and return result.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        ValueError: If param2 is negative
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")
    return len(param1) > param2
```

### 5. Keep Functions Small
- Max 50 lines per function
- Max 15 complexity (cyclomatic)
- Single responsibility

### 6. Avoid Deep Nesting
```python
# Bad
if condition1:
    if condition2:
        if condition3:
            do_something()

# Good
if not condition1:
    return
if not condition2:
    return
if not condition3:
    return
do_something()
```

## Troubleshooting

### Black and Flake8 Conflict

If Black and Flake8 disagree, Black wins. Add the conflicting rule to `.flake8` ignore list.

### Pylint False Positives

Disable specific warnings in code:

```python
# pylint: disable=invalid-name
x = 5  # Short variable name is OK here
```

Or in configuration:

```toml
[tool.pylint.messages_control]
disable = ["C0103"]
```

### Performance Issues

If linting is slow:

```bash
# Run linters in parallel
make lint &
make security &
wait
```

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)

## Summary

1. **Always run `make format` before committing**
2. **Use `make lint` to check for issues**
3. **Fix issues incrementally, not all at once**
4. **Understand why rules exist before ignoring them**
5. **Keep code clean, readable, and maintainable**
