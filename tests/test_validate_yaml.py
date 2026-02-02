#!/usr/bin/env python3
"""Tests for validate_yaml schema validation."""

from validate_yaml import load_schema, validate_vehicle_file


class TestLoadSchema:
    """Tests for load_schema function."""

    def test_returns_dict(self):
        schema = load_schema()
        assert isinstance(schema, dict)

    def test_has_expected_structure(self):
        schema = load_schema()
        assert "type" in schema or "properties" in schema
        assert "car" in schema.get("properties", schema)
        assert "rules" in schema.get("properties", schema)


class TestValidateVehicleFile:
    """Tests for validate_vehicle_file function."""

    def test_valid_minimal_returns_no_errors(self, tmp_path):
        """Valid minimal vehicle file returns empty error list."""
        path = tmp_path / "valid.yaml"
        path.write_text("""
car:
  make: Subaru
  model: BRZ
  year: 2015
  purchaseDate: '2016-11-12'
  purchaseMiles: 21216

rules:
  - item: engine oil and filter
    verb: replace
    intervalMiles: 7500
""")
        schema = load_schema()
        errors = validate_vehicle_file(path, schema)
        assert errors == []

    def test_missing_required_car_field_returns_errors(self, tmp_path):
        """Missing required car field returns schema validation errors."""
        path = tmp_path / "invalid.yaml"
        path.write_text("""
car:
  make: Subaru
  model: BRZ
  year: 2015
  purchaseDate: '2016-11-12'
  # purchaseMiles missing

rules: []
""")
        schema = load_schema()
        errors = validate_vehicle_file(path, schema)
        assert len(errors) >= 1
        assert any(
            "Schema validation" in e or "validation" in e.lower() for e in errors
        )

    def test_invalid_yaml_returns_parse_error(self, tmp_path):
        """Invalid YAML syntax returns YAML parse error."""
        path = tmp_path / "bad.yaml"
        path.write_text("""
car:
  make: Subaru
  model: BRZ
  invalid: [unclosed
""")
        schema = load_schema()
        errors = validate_vehicle_file(path, schema)
        assert len(errors) >= 1
        assert any("YAML" in e for e in errors)

    def test_nonexistent_file_returns_errors(self, tmp_path):
        """Nonexistent file returns error (caught by validate_vehicle_file)."""
        schema = load_schema()
        path = tmp_path / "does_not_exist.yaml"
        errors = validate_vehicle_file(path, schema)
        assert len(errors) >= 1
        assert any(
            "Error" in e or "exist" in e.lower() or "found" in e.lower() for e in errors
        )
