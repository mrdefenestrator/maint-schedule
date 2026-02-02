#!/usr/bin/env python3
"""Tests for YAML loading and saving utilities."""

from pathlib import Path

import pytest
import yaml

from models import (
    load_vehicle,
    save_history_entry,
    save_current_miles,
    update_history_entry,
    delete_history_entry,
    add_rule,
    update_rule,
    delete_rule,
    Car,
    Rule,
    HistoryEntry,
    Vehicle,
)

# =============================================================================
# load_vehicle tests
# =============================================================================


class TestLoadVehicle:
    """Tests for load_vehicle function."""

    def test_loads_minimal_vehicle(self, tmp_path):
        """Load a minimal valid vehicle file."""
        yaml_content = """
car:
  make: Subaru
  model: BRZ
  trim: Premium
  year: 2015
  purchaseDate: '2016-11-12'
  purchaseMiles: 21216

rules:
  - item: engine oil and filter
    verb: replace
    intervalMiles: 7500
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        vehicle = load_vehicle(yaml_file)

        assert isinstance(vehicle, Vehicle)
        assert isinstance(vehicle.car, Car)
        assert vehicle.car.make == "Subaru"
        assert vehicle.car.model == "BRZ"
        assert vehicle.car.year == 2015
        assert vehicle.car.purchase_miles == 21216
        assert len(vehicle.rules) == 1
        assert isinstance(vehicle.rules[0], Rule)
        assert vehicle.rules[0].item == "engine oil and filter"
        assert vehicle.rules[0].interval_miles == 7500

    def test_loads_vehicle_with_history(self, tmp_path):
        """Load a vehicle file with history entries."""
        yaml_content = """
car:
  make: Subaru
  model: WRX
  trim: Limited
  year: 2012
  purchaseDate: '2012-03-23'
  purchaseMiles: 6

rules:
  - item: engine oil and filter
    verb: replace
    intervalMiles: 7500

history:
  - ruleKey: engine oil and filter/replace
    date: '2025-01-15'
    mileage: 95000
    performedBy: self
    notes: Motul 5W-30
    cost: 45.00
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        vehicle = load_vehicle(yaml_file)

        assert len(vehicle.history) == 1
        assert isinstance(vehicle.history[0], HistoryEntry)
        assert vehicle.history[0].rule_key == "engine oil and filter/replace"
        assert vehicle.history[0].mileage == 95000
        assert vehicle.history[0].performed_by == "self"
        assert vehicle.history[0].cost == 45.00

    def test_loads_vehicle_with_state(self, tmp_path):
        """Load a vehicle file with explicit state."""
        yaml_content = """
car:
  make: Subaru
  model: BRZ
  trim: Premium
  year: 2015
  purchaseDate: '2016-11-12'
  purchaseMiles: 21216

state:
  currentMiles: 60000
  asOfDate: '2025-01-15'

rules:
  - item: oil
    verb: replace
    intervalMiles: 7500
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        vehicle = load_vehicle(yaml_file)

        assert vehicle.current_miles == 60000
        assert vehicle.as_of_date == "2025-01-15"

    def test_loads_rule_with_all_fields(self, tmp_path):
        """Load a rule with all optional fields."""
        yaml_content = """
car:
  make: Subaru
  model: BRZ
  trim: Premium
  year: 2015
  purchaseDate: '2016-11-12'
  purchaseMiles: 21216

rules:
  - item: engine coolant
    verb: replace
    phase: ongoing
    intervalMiles: 75000
    intervalMonths: 72
    severeIntervalMiles: 60000
    severeIntervalMonths: 60
    notes: Use Subaru Super Coolant
    startMiles: 137500
    stopMiles: 999999
    aftermarket: false
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        vehicle = load_vehicle(yaml_file)
        rule = vehicle.rules[0]

        assert rule.item == "engine coolant"
        assert rule.verb == "replace"
        assert rule.phase == "ongoing"
        assert rule.interval_miles == 75000
        assert rule.interval_months == 72
        assert rule.severe_interval_miles == 60000
        assert rule.severe_interval_months == 60
        assert rule.notes == "Use Subaru Super Coolant"
        assert rule.start_miles == 137500
        assert rule.stop_miles == 999999
        assert rule.aftermarket is False

    def test_accepts_path_object(self, tmp_path):
        """load_vehicle accepts Path objects."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []
"""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)

        # Ensure Path works (not just str)
        vehicle = load_vehicle(Path(yaml_file))
        assert vehicle.car.make == "Test"


# =============================================================================
# save_history_entry tests
# =============================================================================


class TestSaveHistoryEntry:
    """Tests for save_history_entry function."""

    def test_appends_entry_to_empty_history(self, tmp_path):
        """Append entry to vehicle with no history."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules:
  - item: oil
    verb: replace
    intervalMiles: 7500
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-01-15",
            mileage=50000,
            performed_by="self",
        )

        save_history_entry(yaml_file, entry)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert "history" in data
        assert len(data["history"]) == 1
        assert data["history"][0]["ruleKey"] == "oil/replace"
        assert data["history"][0]["date"] == "2025-01-15"
        assert data["history"][0]["mileage"] == 50000
        assert data["history"][0]["performedBy"] == "self"

    def test_appends_entry_to_existing_history(self, tmp_path):
        """Append entry to vehicle with existing history."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-01-15",
            mileage=50000,
        )

        save_history_entry(yaml_file, entry)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["history"]) == 2
        assert data["history"][1]["mileage"] == 50000

    def test_omits_none_values(self, tmp_path):
        """Entry dict omits None values for cleaner YAML."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        # Entry with only required fields
        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-01-15",
        )

        save_history_entry(yaml_file, entry)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        entry_data = data["history"][0]
        assert "ruleKey" in entry_data
        assert "date" in entry_data
        assert "mileage" not in entry_data
        assert "performedBy" not in entry_data
        assert "notes" not in entry_data
        assert "cost" not in entry_data

    def test_saves_all_optional_fields(self, tmp_path):
        """Entry with all fields saves correctly."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-01-15",
            mileage=50000,
            performed_by="Dealer",
            notes="Full synthetic",
            cost=89.99,
        )

        save_history_entry(yaml_file, entry)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        entry_data = data["history"][0]
        assert entry_data["ruleKey"] == "oil/replace"
        assert entry_data["date"] == "2025-01-15"
        assert entry_data["mileage"] == 50000
        assert entry_data["performedBy"] == "Dealer"
        assert entry_data["notes"] == "Full synthetic"
        assert entry_data["cost"] == 89.99


# =============================================================================
# update_history_entry tests
# =============================================================================


class TestUpdateHistoryEntry:
    """Tests for update_history_entry function."""

    def test_replaces_entry_at_index(self, tmp_path):
        """Replace history entry at given index."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
  - ruleKey: oil/replace
    date: '2025-01-15'
    mileage: 50000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-02-01",
            mileage=51000,
            performed_by="Dealer",
            notes="Updated entry",
        )

        update_history_entry(yaml_file, 1, entry)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["history"]) == 2
        assert data["history"][0]["mileage"] == 40000
        assert data["history"][1]["date"] == "2025-02-01"
        assert data["history"][1]["mileage"] == 51000
        assert data["history"][1]["performedBy"] == "Dealer"
        assert data["history"][1]["notes"] == "Updated entry"

    def test_raises_index_error_for_invalid_index(self, tmp_path):
        """Raise IndexError when index is out of range."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        entry = HistoryEntry(rule_key="oil/replace", date="2025-01-15")

        with pytest.raises(IndexError, match="History index 5 out of range"):
            update_history_entry(yaml_file, 5, entry)


# =============================================================================
# delete_history_entry tests
# =============================================================================


class TestDeleteHistoryEntry:
    """Tests for delete_history_entry function."""

    def test_removes_entry_at_index(self, tmp_path):
        """Remove history entry at given index."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
  - ruleKey: oil/replace
    date: '2025-01-15'
    mileage: 50000
  - ruleKey: brake fluid/replace
    date: '2025-02-01'
    mileage: 51000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        delete_history_entry(yaml_file, 1)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["history"]) == 2
        assert data["history"][0]["mileage"] == 40000
        assert data["history"][1]["ruleKey"] == "brake fluid/replace"
        assert data["history"][1]["mileage"] == 51000

    def test_raises_index_error_for_invalid_index(self, tmp_path):
        """Raise IndexError when index is out of range."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(IndexError, match="History index 3 out of range"):
            delete_history_entry(yaml_file, 3)


# =============================================================================
# add_rule tests
# =============================================================================


class TestAddRule:
    """Tests for add_rule function."""

    def test_appends_rule_to_empty_rules(self, tmp_path):
        """Append rule to vehicle with no rules."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        rule = Rule(
            item="cabin air filter",
            verb="replace",
            interval_miles=15000,
            interval_months=12,
        )

        add_rule(yaml_file, rule)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["rules"]) == 1
        assert data["rules"][0]["item"] == "cabin air filter"
        assert data["rules"][0]["verb"] == "replace"
        assert data["rules"][0]["intervalMiles"] == 15000
        assert data["rules"][0]["intervalMonths"] == 12

    def test_appends_rule_to_existing_rules(self, tmp_path):
        """Append rule to vehicle with existing rules."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules:
  - item: oil
    verb: replace
    intervalMiles: 5000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        rule = Rule(item="brake fluid", verb="replace", interval_miles=30000)

        add_rule(yaml_file, rule)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["rules"]) == 2
        assert data["rules"][0]["item"] == "oil"
        assert data["rules"][1]["item"] == "brake fluid"


# =============================================================================
# update_rule tests
# =============================================================================


class TestUpdateRule:
    """Tests for update_rule function."""

    def test_replaces_rule_at_index(self, tmp_path):
        """Replace rule at given index."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules:
  - item: oil
    verb: replace
    intervalMiles: 5000
  - item: brake fluid
    verb: replace
    intervalMiles: 30000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        rule = Rule(
            item="brake fluid",
            verb="replace",
            interval_miles=25000,
            interval_months=24,
            notes="Updated interval",
        )

        update_rule(yaml_file, 1, rule)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["rules"]) == 2
        assert data["rules"][0]["item"] == "oil"
        assert data["rules"][1]["item"] == "brake fluid"
        assert data["rules"][1]["intervalMiles"] == 25000
        assert data["rules"][1]["intervalMonths"] == 24
        assert data["rules"][1]["notes"] == "Updated interval"


# =============================================================================
# delete_rule tests
# =============================================================================


class TestDeleteRule:
    """Tests for delete_rule function."""

    def test_removes_rule_at_index(self, tmp_path):
        """Remove rule at given index."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules:
  - item: oil
    verb: replace
    intervalMiles: 5000
  - item: brake fluid
    verb: replace
    intervalMiles: 30000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        delete_rule(yaml_file, 0)

        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert len(data["rules"]) == 1
        assert data["rules"][0]["item"] == "brake fluid"


# =============================================================================
# save_current_miles tests
# =============================================================================


class TestSaveCurrentMiles:
    """Tests for save_current_miles function."""

    def test_updates_current_miles_when_state_exists(self, tmp_path):
        """Update currentMiles when state section already exists."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

state:
  currentMiles: 50000
  asOfDate: '2025-01-01'

rules: []
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        save_current_miles(yaml_file, 60000)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert data["state"]["currentMiles"] == 60000
        # asOfDate should be preserved
        assert data["state"]["asOfDate"] == "2025-01-01"

    def test_creates_state_section_when_missing(self, tmp_path):
        """Create state section if it doesn't exist."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules: []
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        save_current_miles(yaml_file, 75000)

        # Reload and verify
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        assert "state" in data
        assert data["state"]["currentMiles"] == 75000

    def test_preserves_other_sections(self, tmp_path):
        """Updating currentMiles doesn't affect other sections."""
        yaml_content = """
car:
  make: Test
  model: Car
  trim: Base
  year: 2020
  purchaseDate: '2020-01-01'
  purchaseMiles: 0

rules:
  - item: oil
    verb: replace
    intervalMiles: 7500

history:
  - ruleKey: oil/replace
    date: '2024-06-15'
    mileage: 40000
"""
        yaml_file = tmp_path / "test_vehicle.yaml"
        yaml_file.write_text(yaml_content)

        save_current_miles(yaml_file, 42000)

        # Reload and verify
        vehicle = load_vehicle(yaml_file)

        assert vehicle.current_miles == 42000
        assert len(vehicle.rules) == 1
        assert len(vehicle.history) == 1
        assert vehicle.history[0].mileage == 40000
