# Linting Quick Reference

## 🚀 Quick Fix

```bash
make format-fix
```

## 📋 Common Commands

| Command | Description |
|---------|-------------|
| `make format` | Auto-format with Black |
| `make format-fix` | Auto-fix all linting issues |
| `make lint` | Run all linters |
| `make security` | Run security checks |
| `make check` | Run all quality checks |

## 🔧 Fix Specific Issues

### Line Too Long (E501)
```bash
make format
```

### Multiple Statements on One Line (E704)
```python
# Bad
def func(): ...

# Good
def func():
    ...
```

### Unused Import (F401)
Remove the import or use it.

### Mutable Default (B006)
```python
# Bad
def func(items=[]):
    pass

# Good
def func(items=None):
    if items is None:
        items = []
```

## ⚙️ Configuration Files

- **`.flake8`** - Flake8 config
- **`pyproject.toml`** - Black, Bandit, Pylint config
- **`.github/workflows/build-and-test.yml`** - CI/CD linting

## 📚 Full Documentation

See [docs/LINTING.md](../docs/LINTING.md) for complete guide.

## ✅ Pre-Commit Checklist

- [ ] Run `make format`
- [ ] Run `make lint`
- [ ] Fix any errors
- [ ] Commit changes

## 🎯 Ignored Warnings

These are intentionally ignored (see config):
- B006, B008, B010, B036, B039, B903

## 🆘 Help

If linting fails in CI:
1. Pull latest changes
2. Run `make format-fix`
3. Run `make lint` to verify
4. Commit and push
