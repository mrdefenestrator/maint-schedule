#!/usr/bin/env bash
set -eu

# Ensure mise tools are available
eval "$(mise activate bash)"
mise install

# Create venv and install dependencies with uv
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

echo ""
echo "Setup complete! Run 'source .venv/bin/activate' to activate the environment."
