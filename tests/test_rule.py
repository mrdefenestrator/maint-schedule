#!/usr/bin/env python3
"""Tests for Rule class."""
import pytest
from models import Rule


class TestRule:
    """Tests for Rule class."""

    def test_key_without_phase(self):
        """Key is item/verb when no phase."""
        rule = Rule(item="engine oil", verb="replace", interval_miles=7500)
        assert rule.key == "engine oil/replace"

    def test_key_with_phase(self):
        """Key includes phase when present."""
        rule = Rule(item="engine coolant", verb="replace", phase="initial",
                    interval_miles=137500)
        assert rule.key == "engine coolant/replace/initial"

    def test_base_key_strips_phase(self):
        """Base key is always item/verb without phase."""
        rule = Rule(item="engine coolant", verb="replace", phase="ongoing",
                    interval_miles=75000)
        assert rule.base_key == "engine coolant/replace"

    def test_is_active_at_default_range(self):
        """Rule with default start/stop is always active."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        assert rule.is_active_at(0)
        assert rule.is_active_at(100000)
        assert rule.is_active_at(500000)

    def test_is_active_at_with_start(self):
        """Rule with startMiles only activates after threshold."""
        rule = Rule(item="coolant", verb="replace", interval_miles=75000,
                    start_miles=137500)
        assert not rule.is_active_at(100000)
        assert rule.is_active_at(137500)
        assert rule.is_active_at(200000)

    def test_is_active_at_with_stop(self):
        """Rule with stopMiles deactivates at threshold."""
        rule = Rule(item="coolant", verb="replace", interval_miles=137500,
                    stop_miles=137500)
        assert rule.is_active_at(0)
        assert rule.is_active_at(137499)
        assert not rule.is_active_at(137500)

    def test_is_active_at_with_start_and_stop(self):
        """Rule with both start and stop has bounded range."""
        rule = Rule(item="part", verb="replace", interval_miles=10000,
                    start_miles=50000, stop_miles=100000)
        assert not rule.is_active_at(49999)
        assert rule.is_active_at(50000)
        assert rule.is_active_at(75000)
        assert not rule.is_active_at(100000)
