#!/usr/bin/env python3
"""Tests for Status enum."""

from models import Status


class TestStatus:
    """Tests for Status enum ordering."""

    def test_urgency_ordering(self):
        """Lower value = more urgent."""
        assert Status.OVERDUE.value < Status.DUE_SOON.value
        assert Status.DUE_SOON.value < Status.OK.value
        assert Status.OK.value < Status.INACTIVE.value
        assert Status.INACTIVE.value < Status.UNKNOWN.value

    def test_comparison_by_value(self):
        """Can compare urgency by .value."""
        assert Status.OVERDUE.value < Status.OK.value
        assert Status.DUE_SOON.value < Status.INACTIVE.value
