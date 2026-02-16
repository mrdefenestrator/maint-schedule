# CLAUDE.md

## Project Overview

Vehicle maintenance schedule manager using YAML-based configuration files. Supports mileage and time-based intervals, severe driving conditions, lifecycle rules (phased maintenance), aftermarket parts tracking, and service history logging. Has both a CLI (`maint.py`) and a Flask web UI (`web/app.py`).

## Tech Stack

- Python 3.12 (managed via `uv`, see `requires-python` in pyproject.toml)
- Package manager: `uv` (pyproject.toml, `uv sync`), installed via `mise`
- Virtual environment: `.venv/`
- Flask for web UI (port 5001)
- YAML files as the data store (no database)

## Common Commands

```bash
# Setup
mise run setup             # Install all deps into .venv via uv sync

# Run tests
mise run test              # pytest with coverage

# Format code
mise run format            # ruff formatter
mise run format-check      # check formatting without changing files

# Lint
mise run lint              # ruff linter
mise run lint-fix          # auto-fix lint issues

# Validate vehicle YAML files
mise run validate

# Run all CI checks (format-check, lint, validate, test)
mise run ci

# CLI usage
uv run python maint.py vehicles/wrx.yaml status
uv run python maint.py vehicles/wrx.yaml history

# Web UI
mise run serve
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

- **Ruff** for formatting (88-char line length) and linting (E501 ignored)
- Modern Python: type hints, f-strings, dataclasses
- PEP 8 compliant

## Key Architecture Decisions

- Domain-driven models with computed status (not stored)
- Rules identified by natural keys: `item/verb/phase`
- Lifecycle phases (`initial`, `ongoing`) for rules that change intervals over vehicle life
- Current mileage derived from history if not explicit
- `dateutil.relativedelta` for month-based interval calculations
- YAML SafeLoader for parsing, omit None values on save
