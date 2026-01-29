#!/usr/bin/env python3
"""Tests for HistoryEntry class."""

from models import HistoryEntry


class TestHistoryEntry:
    """Tests for HistoryEntry class."""

    def test_required_attributes(self):
        """Required attributes are stored correctly."""
        entry = HistoryEntry("oil/replace", "2025-01-15")
        assert entry.rule_key == "oil/replace"
        assert entry.date == "2025-01-15"

    def test_optional_attributes(self):
        """Optional attributes are stored correctly."""
        entry = HistoryEntry(
            rule_key="oil/replace",
            date="2025-01-15",
            mileage=50000,
            performed_by="self",
            notes="Used synthetic oil",
            cost=75.50,
        )
        assert entry.mileage == 50000
        assert entry.performed_by == "self"
        assert entry.notes == "Used synthetic oil"
        assert entry.cost == 75.50

    def test_optional_attributes_default_to_none(self):
        """Optional attributes default to None."""
        entry = HistoryEntry("oil/replace", "2025-01-15")
        assert entry.mileage is None
        assert entry.performed_by is None
        assert entry.notes is None
        assert entry.cost is None
