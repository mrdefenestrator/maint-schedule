#!/usr/bin/env python3
"""Tests for calculation helper functions."""
import pytest
from datetime import date
from models import calc_due_miles, calc_due_date, check_status, Status


class TestCalcDueMiles:
    """Tests for calc_due_miles helper function."""

    def test_with_history(self):
        """last_miles + interval when history exists."""
        assert calc_due_miles(50000, 7500) == 57500

    def test_without_history_default_start(self):
        """start_miles + interval when no history (default start=0)."""
        assert calc_due_miles(None, 7500) == 7500

    def test_without_history_custom_start(self):
        """start_miles + interval when no history and part added later."""
        assert calc_due_miles(None, 10000, start_miles=60000) == 70000

    def test_with_history_ignores_start(self):
        """start_miles is ignored when history exists."""
        assert calc_due_miles(65000, 10000, start_miles=60000) == 75000

    def test_no_interval(self):
        """None when no interval defined."""
        assert calc_due_miles(50000, None) is None
        assert calc_due_miles(None, None) is None


class TestCalcDueDate:
    """Tests for calc_due_date helper function."""

    def test_with_history(self):
        """last_date + interval_months when history exists."""
        last = date(2025, 1, 15)
        result = calc_due_date(last, 6)
        assert result == date(2025, 7, 15)

    def test_fractional_months(self):
        """Handles fractional months (converted to days)."""
        last = date(2025, 1, 15)
        result = calc_due_date(last, 7.5)  # 7 months + 15 days
        assert result == date(2025, 8, 30)

    def test_without_history(self):
        """None when no history (can't calculate date-based due)."""
        assert calc_due_date(None, 6) is None

    def test_no_interval(self):
        """None when no interval defined."""
        assert calc_due_date(date(2025, 1, 15), None) is None


class TestCheckStatus:
    """Tests for check_status helper function."""

    def test_overdue(self):
        """OVERDUE when current >= due."""
        assert check_status(100, 90, 10) == Status.OVERDUE
        assert check_status(100, 100, 10) == Status.OVERDUE

    def test_due_soon(self):
        """DUE_SOON when current >= due - threshold."""
        assert check_status(95, 100, 10) == Status.DUE_SOON
        assert check_status(90, 100, 10) == Status.DUE_SOON

    def test_ok(self):
        """OK when current < due - threshold."""
        assert check_status(80, 100, 10) == Status.OK
        assert check_status(0, 100, 10) == Status.OK
