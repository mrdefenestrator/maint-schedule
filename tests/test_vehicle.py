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

    def test_get_last_service_for_item_prefers_entries_with_mileage(self, car):
        """Prefers entries with mileage over those without."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15"),  # No mileage
                HistoryEntry("oil/replace", "2024-07-15", mileage=87500),
                HistoryEntry("oil/replace", "2025-01-20"),  # More recent but no mileage
            ],
        )
        last = vehicle.get_last_service_for_item("oil", "replace")
        assert last.mileage == 87500
        assert last.date == "2024-07-15"

    def test_get_last_service_for_item_all_without_mileage(self, car):
        """When all entries lack mileage, returns most recent by date."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("coolant/inspect", "2024-01-15"),
                HistoryEntry("coolant/inspect", "2025-01-15"),
                HistoryEntry("coolant/inspect", "2024-07-15"),
            ],
        )
        last = vehicle.get_last_service_for_item("coolant", "inspect")
        assert last.date == "2025-01-15"
        assert last.mileage is None


class TestVehicleLastServiceProperty:
    """Tests for Vehicle.last_service property."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_last_service_returns_most_recent(self, car):
        """Returns the most recent service entry overall."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        last = vehicle.last_service
        assert last.rule_key == "tires/rotate"
        assert last.date == "2025-01-15"

    def test_last_service_returns_none_when_no_history(self, car):
        """Returns None when vehicle has no history."""
        vehicle = Vehicle(car=car, rules=[], history=[])
        assert vehicle.last_service is None


class TestVehicleGetRule:
    """Tests for Vehicle.get_rule method."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_get_rule_finds_matching_rule(self, car):
        """Finds and returns rule with matching key."""
        rules = [
            Rule(item="oil", verb="replace", interval_miles=7500),
            Rule(item="tires", verb="rotate", interval_miles=7500),
            Rule(item="coolant", verb="replace", interval_miles=137500),
        ]
        vehicle = Vehicle(car=car, rules=rules, history=[])

        rule = vehicle.get_rule("tires/rotate")
        assert rule is not None
        assert rule.item == "tires"
        assert rule.verb == "rotate"

    def test_get_rule_returns_none_when_not_found(self, car):
        """Returns None when rule key doesn't match any rule."""
        rules = [
            Rule(item="oil", verb="replace", interval_miles=7500),
        ]
        vehicle = Vehicle(car=car, rules=rules, history=[])

        rule = vehicle.get_rule("nonexistent/rule")
        assert rule is None


class TestVehicleGetHistoryForRule:
    """Tests for Vehicle.get_history_for_rule method."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_get_history_for_rule_returns_matching_entries(self, car):
        """Returns all entries matching the rule key."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2024-02-15", mileage=82500),
                HistoryEntry("oil/replace", "2024-07-15", mileage=87500),
                HistoryEntry("oil/replace", "2025-01-15", mileage=95000),
            ],
        )
        entries = vehicle.get_history_for_rule("oil/replace")
        assert len(entries) == 3
        assert all(e.rule_key == "oil/replace" for e in entries)

    def test_get_history_for_rule_returns_empty_list_when_no_match(self, car):
        """Returns empty list when no entries match."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
            ],
        )
        entries = vehicle.get_history_for_rule("coolant/replace")
        assert entries == []


class TestVehicleGetLastService:
    """Tests for Vehicle.get_last_service method."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_get_last_service_returns_most_recent_for_rule(self, car):
        """Returns the most recent entry for a specific rule."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("oil/replace", "2024-07-15", mileage=87500),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("oil/replace", "2025-01-10", mileage=94500),
            ],
        )
        last = vehicle.get_last_service("oil/replace")
        assert last.date == "2025-01-10"
        assert last.mileage == 94500

    def test_get_last_service_returns_none_when_no_match(self, car):
        """Returns None when no entries match the rule."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
            ],
        )
        last = vehicle.get_last_service("coolant/replace")
        assert last is None


class TestVehicleGetHistorySorted:
    """Tests for Vehicle.get_history_sorted method."""

    @pytest.fixture
    def car(self):
        return Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)

    def test_sort_by_date_descending(self, car):
        """Sort by date, newest first (default)."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="date", reverse=True)
        assert sorted_history[0].date == "2025-01-15"
        assert sorted_history[1].date == "2024-07-15"
        assert sorted_history[2].date == "2024-01-15"

    def test_sort_by_date_ascending(self, car):
        """Sort by date, oldest first."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="date", reverse=False)
        assert sorted_history[0].date == "2024-01-15"
        assert sorted_history[1].date == "2024-07-15"
        assert sorted_history[2].date == "2025-01-15"

    def test_sort_by_miles_descending(self, car):
        """Sort by mileage, highest first."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="miles", reverse=True)
        assert sorted_history[0].mileage == 95000
        assert sorted_history[1].mileage == 87500
        assert sorted_history[2].mileage == 80000

    def test_sort_by_miles_ascending(self, car):
        """Sort by mileage, lowest first."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="miles", reverse=False)
        assert sorted_history[0].mileage == 80000
        assert sorted_history[1].mileage == 87500
        assert sorted_history[2].mileage == 95000

    def test_sort_by_rule_descending(self, car):
        """Sort by rule key, Z to A."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="rule", reverse=True)
        assert sorted_history[0].rule_key == "tires/rotate"
        assert sorted_history[1].rule_key == "oil/replace"
        assert sorted_history[2].rule_key == "brakes/inspect"

    def test_sort_by_rule_ascending(self, car):
        """Sort by rule key, A to Z."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("tires/rotate", "2025-01-15", mileage=95000),
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="rule", reverse=False)
        assert sorted_history[0].rule_key == "brakes/inspect"
        assert sorted_history[1].rule_key == "oil/replace"
        assert sorted_history[2].rule_key == "tires/rotate"

    def test_sort_handles_missing_mileage(self, car):
        """Entries without mileage sort as 0."""
        vehicle = Vehicle(
            car=car,
            rules=[],
            history=[
                HistoryEntry("oil/replace", "2024-01-15", mileage=80000),
                HistoryEntry("coolant/inspect", "2025-01-15"),  # No mileage
                HistoryEntry("brakes/inspect", "2024-07-15", mileage=87500),
            ],
        )
        sorted_history = vehicle.get_history_sorted(sort_by="miles", reverse=False)
        assert sorted_history[0].mileage is None  # Sorts as 0
        assert sorted_history[1].mileage == 80000
        assert sorted_history[2].mileage == 87500


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
