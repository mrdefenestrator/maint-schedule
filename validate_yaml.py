#!/usr/bin/env python3
"""Validate vehicle YAML files against the schema."""
import sys
from pathlib import Path

import yaml
from jsonschema import validate, ValidationError


def load_schema() -> dict:
    """Load the JSON schema from schema.yaml."""
    schema_path = Path(__file__).parent / "schema.yaml"
    with open(schema_path) as f:
        return yaml.safe_load(f)


def validate_vehicle_file(filepath: Path, schema: dict) -> list[str]:
    """Validate a single vehicle YAML file. Returns list of errors."""
    errors = []
    try:
        with open(filepath) as f:
            data = yaml.safe_load(f)
        validate(instance=data, schema=schema)
    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
    except ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
        if e.path:
            errors.append(f"  at path: {'.'.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Error: {e}")
    return errors


def main():
    """Validate all vehicle YAML files in the vehicles/ directory."""
    schema = load_schema()
    vehicles_dir = Path(__file__).parent / "vehicles"

    if not vehicles_dir.exists():
        print(f"Error: vehicles directory not found: {vehicles_dir}")
        return 1

    yaml_files = list(vehicles_dir.glob("*.yaml")) + list(vehicles_dir.glob("*.yml"))

    if not yaml_files:
        print(f"Warning: No YAML files found in {vehicles_dir}")
        return 0

    all_valid = True
    for filepath in sorted(yaml_files):
        errors = validate_vehicle_file(filepath, schema)
        if errors:
            print(f"FAIL: {filepath.name}")
            for error in errors:
                print(f"  {error}")
            all_valid = False
        else:
            print(f"OK: {filepath.name}")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
