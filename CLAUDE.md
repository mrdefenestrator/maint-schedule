# CLAUDE.md

## Project Overview

Vehicle maintenance schedule manager using YAML-based configuration files. Supports mileage and time-based intervals, severe driving conditions, lifecycle rules (phased maintenance), aftermarket parts tracking, and service history logging. Has both a CLI (`maint.py`) and a Flask web UI (`web/app.py`).

## Tech Stack

- Python 3.12 (managed via `mise`, see `.mise.toml`)
- Package manager: `uv`
- Virtual environment: `.venv/`
- Flask for web UI (port 5001)
- YAML files as the data store (no database)

## Common Commands

```bash
# Setup
./setup.sh                # Install Python, create venv, install deps
source .venv/bin/activate  # Activate venv (also handled by direnv/.envrc)

# Run tests
python -m pytest tests/ -v
pytest tests/ -v --cov=models --cov-report=term-missing

# Format code
black *.py models/ tests/

# Lint
flake8 --ignore=E501 *.py models/ tests/

# Validate vehicle YAML files
python validate_yaml.py

# Run all CI checks (format, lint, validate, test)
./ci.sh

# CLI usage
python maint.py vehicles/wrx.yaml status
python maint.py vehicles/wrx.yaml history

# Web UI
python web/app.py
```

## Project Structure

- `models/` — Core domain models (vehicle, rule, history_entry, service_due, calculations, loader, status enum)
- `tests/` — pytest test suite (~127 tests), 1:1 correspondence with model files
- `web/` — Flask app with Jinja2/Tailwind/HTMX templates
- `vehicles/` — Vehicle YAML data files
- `maint.py` — Unified CLI (argparse subcommands)
- `validate_yaml.py` — Schema validation script
- `schema.yaml` — JSON schema for vehicle YAML files

## Code Style

- **Black** formatter, 88-char line length
- **Flake8** with E203, W503 ignored (setup.cfg); CI also ignores E501
- Modern Python: type hints, f-strings, dataclasses
- PEP 8 compliant

## Key Architecture Decisions

- Domain-driven models with computed status (not stored)
- Rules identified by natural keys: `item/verb/phase`
- Lifecycle phases (`initial`, `ongoing`) for rules that change intervals over vehicle life
- Current mileage derived from history if not explicit
- `dateutil.relativedelta` for month-based interval calculations
- YAML SafeLoader for parsing, omit None values on save
