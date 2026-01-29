#!/usr/bin/env python3
"""
Tests for Vehicle class.

Includes integration tests for the complete service due calculation logic:
1. Fresh at zero - all systems assumed fresh at 0 miles
2. Service-based intervals - next due calculated from actual service, not scheduled
3. Whichever comes first - due when either miles OR time threshold crossed
4. Lifecycle rules - item/verb matching ignores phase for history lookup
5. Start/stop thresholds - rules outside current mileage are INACTIVE
"""

import pytest
from models import Vehicle, Car, Rule, HistoryEntry, ServiceDue, Status

# =============================================================================
# Unit Tests: Vehicle Properties
# =============================================================================


class TestVehicleCurrentMiles:
    """Tests for Vehicle.current_miles auto-computation."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_explicit_state_takes_precedence(self, car):
        """Explicit currentMiles in state overrides history."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[HistoryEntry("oil/replace", "2025-01-15", mileage=50000)],
            state_current_miles=60000,
        )
        assert vehicle.current_miles == 60000

    def test_computed_from_history(self, car):
        """currentMiles is max mileage from history."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2025-01-01", mileage=30000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=35000),
                HistoryEntry("brakes/inspect", "2025-01-10", mileage=32000),
            ],
        )
        assert vehicle.current_miles == 35000

    def test_falls_back_to_purchase_miles(self, car):
        """currentMiles is purchaseMiles when no history."""
        vehicle = Vehicle(car=car, rules=[], history=[])
        assert vehicle.current_miles == 6


class TestVehicleHistoryLookup:
    """Tests for Vehicle history lookup methods."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_get_last_service_for_item_ignores_phase(self, car):
        """History lookup matches on item/verb, ignoring phase."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry(
                    "engine coolant/replace/initial", "2024-06-15", mileage=140000
                ),
            ],
        )
        # Should find the initial phase entry when looking up any coolant replace
        last = vehicle.get_last_service_for_item("engine coolant", "replace")
        assert last is not None
        assert last.mileage == 140000

    def test_get_last_service_for_item_returns_most_recent(self, car):
        """Returns most recent service by date."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("oil/replace", "2024-07-15", mileage=87500),
                HistoryEntry("oil/replace", "2025-01-15", mileage=95000),
            ],
        )
        last = vehicle.get_last_service_for_item("oil", "replace")
        assert last.mileage == 95000

    def test_get_last_service_for_item_no_match(self, car):
        """Returns None when no matching history."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2025-01-15", mileage=95000),
            ],
        )
        last = vehicle.get_last_service_for_item("coolant", "replace")
        assert last is None


# =============================================================================
# Integration Tests: Service Due Calculation
# =============================================================================


class TestServiceDueCalculation:
    """Integration tests for the complete service due calculation logic."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_no_history_due_at_interval_from_zero(self, car):
        """
        Rule: No history → due at intervalMiles from odometer 0
        (Fresh at zero assumption)
        """
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        vehicle = Vehicle(car=car, rules=[rule], history=[], state_current_miles=5000)

        result = vehicle.calculate_service_due(rule)

        assert result.due_miles == 7500  # 0 + 7500
        assert result.status == Status.OK
        assert result.miles_remaining == 2500

    def test_with_history_due_at_last_plus_interval(self, car):
        """
        Rule: Has history → due at last_service_miles + intervalMiles
        (Service-based intervals)
        """
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("oil/replace", "2025-01-15", mileage=94500)],
            state_current_miles=96000,
        )

        result = vehicle.calculate_service_due(rule)

        assert result.due_miles == 102000  # 94500 + 7500
        assert result.last_service_miles == 94500
        assert result.miles_remaining == 6000

    def test_overdue_by_miles(self, car):
        """Status is OVERDUE when current mileage exceeds due mileage."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        vehicle = Vehicle(car=car, rules=[rule], history=[], state_current_miles=10000)

        result = vehicle.calculate_service_due(rule)

        assert result.status == Status.OVERDUE
        assert result.due_miles == 7500
        assert result.miles_remaining == -2500

    def test_overdue_by_date(self, car):
        """
        Rule: Whichever comes first - overdue by date even if OK by miles
        """
        rule = Rule(
            item="oil", verb="replace", interval_miles=7500, interval_months=7.5
        )
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("oil/replace", "2024-01-15", mileage=90000)],
            state_current_miles=91000,  # Only 1000 miles, OK by miles
            state_as_of_date="2025-01-15",  # But 12 months later, overdue by date
        )

        result = vehicle.calculate_service_due(rule)

        assert result.status == Status.OVERDUE
        assert result.miles_remaining == 6500  # Still has miles remaining
        assert result.time_remaining_days < 0  # Overdue by time
        # Due date was ~Aug 2024, now Jan 2025

    def test_due_soon_by_miles(self, car):
        """Status is DUE_SOON when within threshold of due mileage."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[],
            state_current_miles=6800,  # 700 miles remaining, within 1000 threshold
        )

        result = vehicle.calculate_service_due(rule, due_soon_miles=1000)

        assert result.status == Status.DUE_SOON
        assert result.miles_remaining == 700

    def test_time_remaining_calculation(self, car):
        """time_remaining_days is calculated correctly for time-based intervals."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500, interval_months=6)
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("oil/replace", "2025-01-15", mileage=90000)],
            state_current_miles=91000,
            state_as_of_date="2025-03-15",  # 2 months later
        )

        result = vehicle.calculate_service_due(rule)

        # Due date is 2025-07-15 (6 months after last service)
        # Current date is 2025-03-15
        # Remaining: ~4 months = ~120 days
        assert result.time_remaining_days is not None
        assert result.time_remaining_days > 100
        assert result.time_remaining_days < 130

    def test_time_remaining_none_for_miles_only_rule(self, car):
        """time_remaining_days is None when rule has no time interval."""
        rule = Rule(item="tires", verb="rotate", interval_miles=7500)
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("tires/rotate", "2025-01-15", mileage=90000)],
            state_current_miles=91000,
            state_as_of_date="2025-03-15",
        )

        result = vehicle.calculate_service_due(rule)

        assert result.time_remaining_days is None

    def test_lifecycle_rule_initial_phase(self, car):
        """Initial phase rule active before threshold."""
        rule_initial = Rule(
            item="coolant",
            verb="replace",
            phase="initial",
            interval_miles=137500,
            stop_miles=137500,
        )
        vehicle = Vehicle(
            car=car, rules=[rule_initial], history=[], state_current_miles=100000
        )

        result = vehicle.calculate_service_due(rule_initial)

        assert result.status == Status.OK
        assert result.due_miles == 137500
        assert result.miles_remaining == 37500

    def test_lifecycle_rule_initial_becomes_inactive(self, car):
        """Initial phase rule becomes INACTIVE after threshold."""
        rule_initial = Rule(
            item="coolant",
            verb="replace",
            phase="initial",
            interval_miles=137500,
            stop_miles=137500,
        )
        vehicle = Vehicle(
            car=car,
            rules=[rule_initial],
            history=[],
            state_current_miles=140000,  # Past stop threshold
        )

        result = vehicle.calculate_service_due(rule_initial)

        assert result.status == Status.INACTIVE

    def test_lifecycle_rule_ongoing_uses_any_phase_history(self, car):
        """
        Rule: Lifecycle rules - item/verb matching ignores phase
        Ongoing phase finds history logged under initial phase.
        """
        rule_ongoing = Rule(
            item="coolant",
            verb="replace",
            phase="ongoing",
            interval_miles=75000,
            start_miles=137500,
        )
        vehicle = Vehicle(
            car=car,
            rules=[rule_ongoing],
            history=[
                # History logged under "initial" phase
                HistoryEntry("coolant/replace/initial", "2024-06-15", mileage=140000)
            ],
            state_current_miles=180000,
        )

        result = vehicle.calculate_service_due(rule_ongoing)

        assert result.status == Status.OK
        assert result.last_service_miles == 140000  # Found initial phase history
        assert result.due_miles == 215000  # 140000 + 75000
        assert result.miles_remaining == 35000

    def test_severe_mode_uses_severe_intervals(self, car):
        """Severe mode uses severe intervals for calculation."""
        rule = Rule(
            item="oil", verb="replace", interval_miles=7500, severe_interval_miles=3750
        )
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("oil/replace", "2025-01-15", mileage=90000)],
            state_current_miles=92000,
        )

        # Normal mode
        result_normal = vehicle.calculate_service_due(rule, severe=False)
        assert result_normal.due_miles == 97500  # 90000 + 7500

        # Severe mode
        result_severe = vehicle.calculate_service_due(rule, severe=True)
        assert result_severe.due_miles == 93750  # 90000 + 3750

    def test_severe_mode_falls_back_to_normal(self, car):
        """Severe mode falls back to normal interval when severe not defined."""
        rule = Rule(
            item="oil",
            verb="replace",
            interval_miles=7500,  # No severe interval defined
        )
        vehicle = Vehicle(
            car=car,
            rules=[rule],
            history=[HistoryEntry("oil/replace", "2025-01-15", mileage=90000)],
            state_current_miles=92000,
        )

        # Severe mode should fall back to normal interval
        result = vehicle.calculate_service_due(rule, severe=True)
        assert result.due_miles == 97500  # Falls back to 90000 + 7500

    def test_time_only_rule_unknown_without_history(self, car):
        """Time-only rule with no history is UNKNOWN."""
        rule = Rule(item="airbags", verb="inspect", interval_months=120)
        vehicle = Vehicle(car=car, rules=[rule], history=[], state_current_miles=100000)

        result = vehicle.calculate_service_due(rule)

        assert result.status == Status.UNKNOWN
        assert result.due_miles is None
        assert result.due_date is None

    def test_aftermarket_part_with_start_miles(self, car):
        """
        Rule: Start/stop thresholds - parts added later (aftermarket)
        Part added at 60000 miles, rule not active before that.
        """
        rule = Rule(
            item="cusco lsd fluid",
            verb="replace",
            interval_miles=10000,
            start_miles=60000,
            aftermarket=True,
        )

        # Before part was installed
        vehicle_before = Vehicle(
            car=car, rules=[rule], history=[], state_current_miles=50000
        )
        result_before = vehicle_before.calculate_service_due(rule)
        assert result_before.status == Status.INACTIVE

        # After part was installed
        vehicle_after = Vehicle(
            car=car, rules=[rule], history=[], state_current_miles=65000
        )
        result_after = vehicle_after.calculate_service_due(rule)
        assert result_after.status == Status.OK
        assert result_after.due_miles == 70000  # start_miles + interval = 60k + 10k
        assert result_after.miles_remaining == 5000


class TestGetAllServiceStatus:
    """Tests for getting status of all rules at once."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_returns_status_for_all_rules(self, car):
        """Returns ServiceDue for every rule."""
        rules = [
            Rule(item="oil", verb="replace", interval_miles=7500),
            Rule(item="tires", verb="rotate", interval_miles=7500),
            Rule(item="coolant", verb="replace", interval_miles=137500),
        ]
        vehicle = Vehicle(car=car, rules=rules, history=[], state_current_miles=50000)

        statuses = vehicle.get_all_service_status()

        assert len(statuses) == 3
        assert all(isinstance(s, ServiceDue) for s in statuses)

    def test_filters_by_status(self, car):
        """Can filter results by status category."""
        rules = [
            Rule(item="oil", verb="replace", interval_miles=7500),  # Overdue at 50k
            Rule(item="coolant", verb="replace", interval_miles=137500),  # OK
            Rule(
                item="lsd", verb="replace", interval_miles=10000, start_miles=60000
            ),  # Inactive
        ]
        vehicle = Vehicle(car=car, rules=rules, history=[], state_current_miles=50000)

        statuses = vehicle.get_all_service_status()

        overdue = [s for s in statuses if s.status == Status.OVERDUE]
        ok = [s for s in statuses if s.status == Status.OK]
        inactive = [s for s in statuses if s.status == Status.INACTIVE]

        assert len(overdue) == 1
        assert overdue[0].rule.item == "oil"
        assert len(ok) == 1
        assert ok[0].rule.item == "coolant"
        assert len(inactive) == 1
        assert inactive[0].rule.item == "lsd"
