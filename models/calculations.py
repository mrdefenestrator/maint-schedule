"""Helper functions for service due calculations."""

from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Optional

from .status import Status


def calc_due_miles(
    last_miles: Optional[float], interval: Optional[float], start_miles: float = 0
) -> Optional[float]:
    """
    Calculate next due mileage.

    - With history: last_miles + interval
    - Without history: start_miles + interval (accounts for parts added later)
    """
    if interval is None:
        return None
    if last_miles is not None:
        return last_miles + interval
    return start_miles + interval


def calc_due_date(
    last_date: Optional[date], interval_months: Optional[float]
) -> Optional[date]:
    """Calculate next due date: last + interval months."""
    if interval_months is None or last_date is None:
        return None
    months = int(interval_months)
    days = int((interval_months - months) * 30)
    return last_date + relativedelta(months=months, days=days)


def check_status(current: float, due: float, soon_threshold: float) -> Status:
    """Determine status by comparing current value to due threshold."""
    if current >= due:
        return Status.OVERDUE
    if current >= due - soon_threshold:
        return Status.DUE_SOON
    return Status.OK
