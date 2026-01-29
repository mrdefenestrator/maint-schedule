#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure mise tools are available
eval "$(mise activate bash)"

# Activate venv
source .venv/bin/activate

echo "================================"
echo "Running CI checks"
echo "================================"
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

fail() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# --------------------------------
# Python code formatting (black)
# --------------------------------
echo "Checking Python code formatting (black)..."
if black --check --quiet *.py models/ tests/; then
    success "Black formatting check passed"
else
    fail "Black formatting check failed. Run 'black *.py models/ tests/' to fix."
fi
echo

# --------------------------------
# Python linting (flake8)
# --------------------------------
echo "Checking Python linting (flake8)..."
if flake8 *.py models/ tests/; then
    success "Flake8 linting passed"
else
    fail "Flake8 linting failed"
fi
echo

# --------------------------------
# YAML schema validation
# --------------------------------
echo "Validating vehicle YAML files against schema..."
if python validate_yaml.py; then
    success "YAML validation passed"
else
    fail "YAML validation failed"
fi
echo

# --------------------------------
# Run tests
# --------------------------------
echo "Running tests..."
if pytest tests/ -v; then
    success "All tests passed"
else
    fail "Tests failed"
fi
echo

echo "================================"
echo -e "${GREEN}All CI checks passed!${NC}"
echo "================================"
