#!/usr/bin/env bash
set -eu

# Ensure mise tools are available
eval "$(mise activate bash)"
mise install

# Create venv and install dependencies with uv
uv venv
source .venv/bin/activate

# Install dev dependencies by default (includes runtime deps)
# Use --prod for runtime-only install
if [[ "${1:-}" == "--prod" ]]; then
    uv pip install -r requirements.txt
    echo ""
    echo "Setup complete (runtime only)! Run 'source .venv/bin/activate' to activate."
else
    uv pip install -r requirements-dev.txt
    echo ""
    echo "Setup complete! Run 'source .venv/bin/activate' to activate the environment."
fi
