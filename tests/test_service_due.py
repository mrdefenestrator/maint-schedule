#!/usr/bin/env python3
"""Tests for ServiceDue dataclass."""
import pytest
from models import ServiceDue, Status, Rule


class TestServiceDue:
    """Tests for ServiceDue dataclass."""

    def test_is_due_overdue(self):
        """is_due returns True when OVERDUE."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OVERDUE)
        assert svc.is_due is True

    def test_is_due_due_soon(self):
        """is_due returns True when DUE_SOON."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.DUE_SOON)
        assert svc.is_due is True

    def test_is_due_ok(self):
        """is_due returns False when OK."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.OK)
        assert svc.is_due is False

    def test_is_due_inactive(self):
        """is_due returns False when INACTIVE."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.INACTIVE)
        assert svc.is_due is False

    def test_is_due_unknown(self):
        """is_due returns False when UNKNOWN."""
        rule = Rule(item="oil", verb="replace", interval_miles=7500)
        svc = ServiceDue(rule=rule, status=Status.UNKNOWN)
        assert svc.is_due is False
