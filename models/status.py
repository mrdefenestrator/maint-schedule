"""Status enum for maintenance urgency levels."""

from enum import Enum


class Status(Enum):
    """Maintenance status categories. Lower value = more urgent."""

    OVERDUE = 1
    DUE_SOON = 2
    OK = 3
    INACTIVE = 4  # Rule doesn't apply at current mileage (start/stop)
    UNKNOWN = 5  # Can't calculate (missing data)
