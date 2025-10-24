#!/bin/bash
# Script to automatically fix common linting errors

set -e

echo "🔧 Fixing linting errors..."
echo ""

# Run black to fix formatting (will handle most line length issues)
echo "Running Black formatter..."
uv run black src/ tests/ --line-length 120

# Run autopep8 for additional fixes
echo "Running autopep8..."
uv run autopep8 --in-place --aggressive --aggressive \
    --max-line-length 120 \
    --recursive src/ tests/

echo ""
echo "✅ Automatic fixes complete!"
echo ""
echo "Remaining issues need manual review:"
echo "- B006: Mutable default arguments"
echo "- B903: Data class __slots__"
echo "- B036: BaseException handling"
echo "- B007: Unused loop variables"
echo "- B010: setattr with constants"
echo "- B039: ContextVar with mutable defaults"
echo ""
echo "Run 'make lint' to check remaining issues"
