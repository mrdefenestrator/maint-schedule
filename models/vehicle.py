"""Vehicle class - the main aggregate for vehicle data and calculations."""

from datetime import date
from typing import List, Optional

from .car import Car
from .rule import Rule
from .history_entry import HistoryEntry
from .service_due import ServiceDue
from .status import Status
from .calculations import calc_due_miles, calc_due_date, check_status


class Vehicle:
    """Complete vehicle record with car info, rules, and maintenance history."""

    def __init__(
        self,
        car: Car,
        rules: List[Rule],
        history: Optional[List[HistoryEntry]] = None,
        state_as_of_date: Optional[str] = None,
        state_current_miles: Optional[float] = None,
    ):
        self.car = car
        self.rules = rules
        self.history = history or []
        self._state_as_of_date = state_as_of_date
        self._state_current_miles = state_current_miles

    @property
    def current_miles(self) -> Optional[float]:
        """Current mileage, auto-computed from history if not explicitly set."""
        if self._state_current_miles is not None:
            return self._state_current_miles
        # Auto-compute from history
        if self.history:
            miles_from_history = [
                h.mileage for h in self.history if h.mileage is not None
            ]
            if miles_from_history:
                return max(miles_from_history)
        return self.car.purchase_miles

    @property
    def as_of_date(self) -> str:
        """Date of current state, defaults to today."""
        if self._state_as_of_date:
            return self._state_as_of_date
        return date.today().isoformat()

    @property
    def last_service(self) -> Optional[HistoryEntry]:
        """Get the most recent service entry overall."""
        if not self.history:
            return None
        return max(self.history, key=lambda h: (h.date, h.mileage or 0))

    def get_rule(self, key: str) -> Optional[Rule]:
        """Find a rule by its natural key."""
        for rule in self.rules:
            if rule.key == key:
                return rule
        return None

    def get_history_for_rule(self, key: str) -> List[HistoryEntry]:
        """Get all history entries for a specific rule."""
        return [h for h in self.history if h.rule_key == key]

    def get_last_service(self, key: str) -> Optional[HistoryEntry]:
        """Get the most recent service for a rule."""
        entries = self.get_history_for_rule(key)
        if not entries:
            return None
        return max(entries, key=lambda h: h.date)

    def get_last_service_for_item(self, item: str, verb: str) -> Optional[HistoryEntry]:
        """
        Get the most recent service for an item/verb combination,
        regardless of phase. Used for lifecycle rules where history
        may be logged under different phases.
        """
        base_key = f"{item}/{verb}"
        matching = [h for h in self.history if h.rule_key.startswith(base_key)]
        if not matching:
            return None
        # Prefer entries with mileage for calculation
        with_mileage = [h for h in matching if h.mileage is not None]
        if with_mileage:
            return max(with_mileage, key=lambda h: (h.date, h.mileage))
        return max(matching, key=lambda h: h.date)

    def get_history_sorted(
        self, sort_by: str = "date", reverse: bool = True
    ) -> List[HistoryEntry]:
        """
        Get history entries sorted by specified field.

        Args:
            sort_by: "date", "miles", or "rule"
            reverse: If True, newest/highest first (default)
        """
        if sort_by == "date":
            return sorted(self.history, key=lambda h: h.date, reverse=reverse)
        elif sort_by == "miles":
            return sorted(self.history, key=lambda h: h.mileage or 0, reverse=reverse)
        elif sort_by == "rule":
            return sorted(
                self.history, key=lambda h: (h.rule_key, h.date), reverse=reverse
            )
        return self.history

    def calculate_service_due(
        self,
        rule: Rule,
        due_soon_miles: float = 1000,
        due_soon_months: float = 1,
        severe: bool = False,
    ) -> ServiceDue:
        """
        Calculate when a service is due for a given rule.

        Logic:
        - If rule is not active at current mileage: status = INACTIVE
        - Find last service for this item/verb (any phase)
        - If no history: due at startMiles + intervalMiles
        - If has history: due at last_service_miles + intervalMiles
        - Compare to current miles/date to determine status

        Args:
            severe: If True, use severe intervals (falls back to normal if not defined)
        """
        current_miles = self.current_miles
        current_date = date.fromisoformat(self.as_of_date)

        # Check if rule is active at current mileage
        if not rule.is_active_at(current_miles):
            return ServiceDue(rule=rule, status=Status.INACTIVE)

        # Find last service (match on item/verb, ignore phase)
        last_service = self.get_last_service_for_item(rule.item, rule.verb)
        last_miles = last_service.mileage if last_service else None
        last_date_str = last_service.date if last_service else None
        last_date = date.fromisoformat(last_date_str) if last_date_str else None

        # Select intervals based on mode (severe falls back to normal if not defined)
        if severe:
            interval_miles = rule.severe_interval_miles or rule.interval_miles
            interval_months = rule.severe_interval_months or rule.interval_months
        else:
            interval_miles = rule.interval_miles
            interval_months = rule.interval_months

        # Calculate due points
        due_miles = calc_due_miles(last_miles, interval_miles, rule.start_miles)
        due_date = calc_due_date(last_date, interval_months)

        # Determine status
        if due_miles is None and due_date is None:
            status = Status.UNKNOWN
        else:
            status = Status.OK
            if due_miles is not None:
                status = check_status(current_miles, due_miles, due_soon_miles)
            if due_date is not None:
                date_status = check_status(
                    current_date.toordinal(),
                    due_date.toordinal(),
                    int(due_soon_months * 30),
                )
                # Escalate status if date check is worse
                if date_status.value < status.value:  # OVERDUE < DUE_SOON < OK
                    status = date_status

        miles_remaining = (due_miles - current_miles) if due_miles else None

        return ServiceDue(
            rule=rule,
            status=status,
            last_service_miles=last_miles,
            last_service_date=last_date_str,
            due_miles=due_miles,
            due_date=due_date.isoformat() if due_date else None,
            severe_due_miles=None,
            severe_due_date=None,
            miles_remaining=miles_remaining,
        )

    def get_all_service_status(
        self,
        due_soon_miles: float = 1000,
        due_soon_months: float = 1,
        severe: bool = False,
    ) -> List[ServiceDue]:
        """Calculate service status for all active rules."""
        return [
            self.calculate_service_due(rule, due_soon_miles, due_soon_months, severe)
            for rule in self.rules
        ]
