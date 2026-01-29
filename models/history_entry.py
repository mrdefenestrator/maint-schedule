"""HistoryEntry class for maintenance records."""
from typing import Optional


class HistoryEntry:
    """A record of maintenance performed."""

    def __init__(
            self,
            rule_key: str,
            date: str,
            mileage: Optional[float] = None,
            performed_by: Optional[str] = None,
            notes: Optional[str] = None,
            cost: Optional[float] = None,
    ):
        self.rule_key = rule_key
        self.date = date
        self.mileage = mileage
        self.performed_by = performed_by
        self.notes = notes
        self.cost = cost
