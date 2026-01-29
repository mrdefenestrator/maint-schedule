"""Rule class for maintenance interval definitions."""
from typing import Optional


class Rule:
    """A maintenance rule defining when a service should be performed."""

    def __init__(
            self,
            item: str,
            verb: str,
            interval_miles: Optional[float] = None,
            interval_months: Optional[float] = None,
            severe_interval_miles: Optional[float] = None,
            severe_interval_months: Optional[float] = None,
            notes: Optional[str] = None,
            phase: Optional[str] = None,
            start_miles: float = 0,
            stop_miles: float = 999999999,
            start_months: float = 0,
            stop_months: float = 9999,
            aftermarket: bool = False,
    ):
        self.item = item
        self.verb = verb
        self.phase = phase
        self.interval_miles = interval_miles
        self.interval_months = interval_months
        self.severe_interval_miles = severe_interval_miles
        self.severe_interval_months = severe_interval_months
        self.notes = notes
        self.start_miles = start_miles or 0
        self.stop_miles = stop_miles or 999999999
        self.start_months = start_months or 0
        self.stop_months = stop_months or 9999
        self.aftermarket = aftermarket or False

    @property
    def key(self) -> str:
        """Generate natural key from item/verb/phase."""
        base = f"{self.item}/{self.verb}"
        if self.phase:
            return f"{base}/{self.phase}"
        return base

    @property
    def base_key(self) -> str:
        """Generate base key from item/verb (without phase)."""
        return f"{self.item}/{self.verb}"

    def is_active_at(self, miles: float) -> bool:
        """Check if this rule applies at the given mileage."""
        return self.start_miles <= miles < self.stop_miles
