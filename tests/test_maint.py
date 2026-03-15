#!/usr/bin/env python3
"""Tests for maint CLI formatting and table helpers."""

from models import Car, Rule, HistoryEntry, ServiceDue, Status, Vehicle
from maint import (
    format_miles,
    format_cost,
    format_remaining,
    format_time_remaining,
    truncate,
    make_status_table,
    make_history_table,
    extract_chart_data,
    cmd_chart,
)


class TestFormatMiles:
    """Tests for format_miles."""

    def test_formats_number(self):
        assert format_miles(50000) == "50,000"
        assert format_miles(0) == "0"

    def test_none_returns_dash(self):
        assert format_miles(None) == "-"


class TestFormatCost:
    """Tests for format_cost."""

    def test_formats_number(self):
        assert format_cost(75.50) == "$75.50"
        assert format_cost(0) == "$0.00"

    def test_none_returns_dash(self):
        assert format_cost(None) == "-"


class TestFormatRemaining:
    """Tests for format_remaining."""

    def test_none_returns_dash(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK, miles_remaining=None)
        assert format_remaining(svc) == "-"

    def test_positive_remaining(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK, miles_remaining=2500)
        assert format_remaining(svc) == "2,500"

    def test_negative_remaining_overdue(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OVERDUE, miles_remaining=-1500)
        assert format_remaining(svc) == "-1,500"


class TestFormatTimeRemaining:
    """Tests for format_time_remaining."""

    def test_none_returns_dash(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK, time_remaining_days=None)
        assert format_time_remaining(svc) == "-"

    def test_positive_months_and_days(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK, time_remaining_days=105)
        assert format_time_remaining(svc) == "3mo 15d"

    def test_positive_days_only(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK, time_remaining_days=14)
        assert format_time_remaining(svc) == "14d"

    def test_negative_overdue_months(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OVERDUE, time_remaining_days=-65)
        assert format_time_remaining(svc) == "-2mo 5d"

    def test_negative_overdue_days_only(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OVERDUE, time_remaining_days=-10)
        assert format_time_remaining(svc) == "-10d"


class TestTruncate:
    """Tests for truncate."""

    def test_none_returns_dash(self):
        assert truncate(None) == "-"

    def test_short_text_unchanged(self):
        assert truncate("short") == "short"
        assert (
            truncate("exactly thirty chars!!!!!!!!!!", max_len=30)
            == "exactly thirty chars!!!!!!!!!!"
        )

    def test_long_text_truncated_with_ellipsis(self):
        # max_len=15 → 12 chars + "..." = 15 total
        assert truncate("this is a very long note", max_len=15) == "this is a ve..."

    def test_custom_max_len(self):
        assert truncate("hello world", max_len=8) == "hello..."


class TestMakeStatusTable:
    """Tests for make_status_table."""

    def test_empty_list_returns_empty_rows(self):
        assert make_status_table([]) == []

    def test_single_service_row(self):
        rule = Rule(item="engine oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(
            rule=rule,
            status=Status.OK,
            last_service_date="2025-01-15",
            last_service_miles=94500,
            due_miles=102000,
            due_date="2025-07-15",
            miles_remaining=6000,
            time_remaining_days=120,
        )
        rows = make_status_table([svc])
        assert len(rows) == 1
        assert rows[0][0] == "Replace - engine oil"
        assert rows[0][1] == "2025-01-15 @ 94,500"
        assert rows[0][2] == "102,000"
        assert rows[0][3] == "2025-07-15"
        assert rows[0][4] == "6,000"
        assert rows[0][5] == "4mo 0d"

    def test_last_done_dash_when_no_history(self):
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(
            rule=rule,
            status=Status.UNKNOWN,
            due_miles=7500,
            due_date=None,
            miles_remaining=None,
            time_remaining_days=None,
        )
        rows = make_status_table([svc])
        assert rows[0][1] == "-"


class TestMakeHistoryTable:
    """Tests for make_history_table."""

    def test_converts_entries_to_rows(self):
        car = Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)
        rules = [Rule(item="oil", verb="replace", interval_miles=7500)]
        vehicle = Vehicle(car=car, rules=rules, history=[])
        entries = [
            HistoryEntry(
                "oil/replace",
                "2025-01-15",
                mileage=95000,
                performed_by="self",
                cost=45.0,
                notes="Motul",
            ),
        ]
        rows = make_history_table(entries, vehicle)
        assert len(rows) == 1
        assert rows[0][0] == "2025-01-15"
        assert rows[0][1] == "95,000"
        assert rows[0][2] == "Replace - oil"
        assert rows[0][3] == "self"
        assert rows[0][4] == "$45.00"
        assert "Motul" in rows[0][5]

    def test_show_index_adds_first_column(self):
        car = Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)
        rules = [Rule(item="oil", verb="replace", interval_miles=7500)]
        vehicle = Vehicle(car=car, rules=rules, history=[])
        entries = [HistoryEntry("oil/replace", "2025-01-15", mileage=95000)]
        rows = make_history_table(entries, vehicle, show_index=True, indices=[0])
        assert len(rows) == 1
        assert rows[0][0] == "0"
        assert rows[0][1] == "2025-01-15"

    def test_unknown_rule_key_uses_key_as_display(self):
        car = Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)
        vehicle = Vehicle(car=car, rules=[], history=[])
        entries = [HistoryEntry("deleted/rule", "2025-01-15")]
        rows = make_history_table(entries, vehicle)
        assert rows[0][2] == "deleted/rule"


class TestExtractChartData:
    """Tests for extract_chart_data."""

    def _make_vehicle(self, history=None):
        car = Car(
            make="Test",
            model="Car",
            trim=None,
            year=2020,
            purchase_date="2020-01-01",
            purchase_miles=100,
        )
        return Vehicle(car=car, rules=[], history=history or [])

    def test_no_history_returns_none(self):
        vehicle = self._make_vehicle()
        assert extract_chart_data(vehicle) is None

    def test_single_entry_returns_none(self):
        """Purchase point + 0 history entries with mileage = 1 point total."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=None)
            ]
        )
        assert extract_chart_data(vehicle) is None

    def test_basic_extraction(self):
        """Purchase + 2 entries = 3 line points, 2 single markers."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=5000),
                HistoryEntry(rule_key="oil/replace", date="2021-01-01", mileage=10000),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        assert result["line_dates"] == ["2020-01-01", "2020-06-01", "2021-01-01"]
        assert result["line_mileages"] == [100, 5000, 10000]
        assert len(result["single_dates"]) == 2
        assert len(result["multi_dates"]) == 0

    def test_grouped_markers(self):
        """Two services on same date/mileage create a multi marker."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=5000),
                HistoryEntry(rule_key="tires/rotate", date="2020-06-01", mileage=5000),
                HistoryEntry(rule_key="oil/replace", date="2021-01-01", mileage=10000),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        assert len(result["line_dates"]) == 3
        assert result["single_dates"] == ["2021-01-01"]
        assert result["single_mileages"] == [10000]
        assert result["multi_dates"] == ["2020-06-01"]
        assert result["multi_mileages"] == [5000]

    def test_rule_filter(self):
        """--rule filter only affects markers, not line data."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=5000),
                HistoryEntry(rule_key="tires/rotate", date="2020-06-01", mileage=5000),
                HistoryEntry(rule_key="oil/replace", date="2021-01-01", mileage=10000),
            ]
        )
        result = extract_chart_data(vehicle, rule_filter="oil")
        assert result is not None
        assert len(result["line_dates"]) == 3
        assert len(result["single_dates"]) == 2
        assert len(result["multi_dates"]) == 0

    def test_entries_without_mileage_excluded(self):
        """History entries with mileage=None are excluded from everything."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=None),
                HistoryEntry(rule_key="oil/replace", date="2021-01-01", mileage=10000),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        assert len(result["line_dates"]) == 2
        assert result["line_dates"] == ["2020-01-01", "2021-01-01"]

    def test_sorted_by_date(self):
        """Output is sorted by date regardless of input order."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(rule_key="oil/replace", date="2021-01-01", mileage=10000),
                HistoryEntry(rule_key="oil/replace", date="2020-06-01", mileage=5000),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result["line_dates"] == ["2020-01-01", "2020-06-01", "2021-01-01"]


class TestCmdChartEdgeCases:
    """Tests for cmd_chart error message selection."""

    def test_no_history_message(self, capsys, tmp_path):
        """No history at all -> 'No mileage data to chart.'"""
        import argparse

        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(
            "car:\n  make: Test\n  model: Car\n  trim: Base\n"
            "  year: 2020\n  purchaseDate: '2020-01-01'\n  purchaseMiles: 100\n"
            "history: []\nrules: []\n"
        )
        args = argparse.Namespace(vehicle_file=yaml_path, rule=None)
        result = cmd_chart(args)
        assert result == 0
        assert "No mileage data to chart." in capsys.readouterr().out

    def test_only_null_mileage_message(self, capsys, tmp_path):
        """History entries but all mileage=None -> 'No mileage data to chart.'"""
        import argparse

        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(
            "car:\n  make: Test\n  model: Car\n  trim: Base\n"
            "  year: 2020\n  purchaseDate: '2020-01-01'\n  purchaseMiles: 100\n"
            "history:\n- ruleKey: oil/replace\n  date: '2020-06-01'\n"
            "rules: []\n"
        )
        args = argparse.Namespace(vehicle_file=yaml_path, rule=None)
        result = cmd_chart(args)
        assert result == 0
        assert "No mileage data to chart." in capsys.readouterr().out
