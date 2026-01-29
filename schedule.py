#!/usr/bin/env python3
import argparse
import json
import yaml
from dataclasses import dataclass
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from enum import Enum
from pathlib import Path
from tabulate import tabulate
from typing import List, Optional


class Status(Enum):
    """Maintenance status categories. Lower value = more urgent."""
    OVERDUE = 1
    DUE_SOON = 2
    OK = 3
    INACTIVE = 4  # Rule doesn't apply at current mileage (start/stop)
    UNKNOWN = 5   # Can't calculate (missing data)


def _calc_due_miles(last_miles: Optional[float], interval: Optional[float],
                    start_miles: float = 0) -> Optional[float]:
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


def _calc_due_date(last_date: Optional[date], interval_months: Optional[float]) -> Optional[date]:
    """Calculate next due date: last + interval months."""
    if interval_months is None or last_date is None:
        return None
    months = int(interval_months)
    days = int((interval_months - months) * 30)
    return last_date + relativedelta(months=months, days=days)


def _check_status(current: float, due: float, soon_threshold: float) -> Status:
    """Determine status by comparing current value to due threshold."""
    if current >= due:
        return Status.OVERDUE
    if current >= due - soon_threshold:
        return Status.DUE_SOON
    return Status.OK


@dataclass
class ServiceDue:
    """Calculated service due information for a rule."""
    rule: 'Rule'
    status: Status
    last_service_miles: Optional[float] = None
    last_service_date: Optional[str] = None
    due_miles: Optional[float] = None
    due_date: Optional[str] = None
    severe_due_miles: Optional[float] = None
    severe_due_date: Optional[str] = None
    miles_remaining: Optional[float] = None

    @property
    def is_due(self) -> bool:
        return self.status in (Status.OVERDUE, Status.DUE_SOON)


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


class Car:
    """Vehicle identification and purchase information."""

    def __init__(self, make: str, model: str, trim: str, year: int,
                 purchase_date: str, purchase_miles: float):
        self.make = make
        self.model = model
        self.trim = trim
        self.year = year
        self.purchase_date = purchase_date
        self.purchase_miles = purchase_miles

    @property
    def name(self) -> str:
        """Human-readable vehicle name."""
        return f"{self.year} {self.make} {self.model} {self.trim}"


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
            miles_from_history = [h.mileage for h in self.history if h.mileage is not None]
            if miles_from_history:
                return max(miles_from_history)
        return self.car.purchase_miles

    @property
    def as_of_date(self) -> str:
        """Date of current state, defaults to today."""
        if self._state_as_of_date:
            return self._state_as_of_date
        return date.today().isoformat()

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

    def calculate_service_due(self, rule: Rule,
                               due_soon_miles: float = 1000,
                               due_soon_months: float = 1) -> ServiceDue:
        """
        Calculate when a service is due for a given rule.

        Logic:
        - If rule is not active at current mileage: status = INACTIVE
        - Find last service for this item/verb (any phase)
        - If no history: due at intervalMiles from odometer 0
        - If has history: due at last_service_miles + intervalMiles
        - Compare to current miles/date to determine status
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

        # Calculate due points (normal and severe)
        due_miles = _calc_due_miles(last_miles, rule.interval_miles, rule.start_miles)
        severe_due_miles = _calc_due_miles(last_miles, rule.severe_interval_miles,
                                           rule.start_miles)
        due_date = _calc_due_date(last_date, rule.interval_months)
        severe_due_date = _calc_due_date(last_date, rule.severe_interval_months)

        # Determine status
        if due_miles is None and due_date is None:
            status = Status.UNKNOWN
        else:
            status = Status.OK
            if due_miles is not None:
                status = _check_status(current_miles, due_miles, due_soon_miles)
            if due_date is not None:
                date_status = _check_status(
                    current_date.toordinal(),
                    due_date.toordinal(),
                    int(due_soon_months * 30)
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
            severe_due_miles=severe_due_miles,
            severe_due_date=severe_due_date.isoformat() if severe_due_date else None,
            miles_remaining=miles_remaining,
        )

    def get_all_service_status(self, due_soon_miles: float = 1000,
                                due_soon_months: float = 1) -> List[ServiceDue]:
        """Calculate service status for all active rules."""
        return [self.calculate_service_due(rule, due_soon_miles, due_soon_months)
                for rule in self.rules]


def _parse_object(dct):
    """Parse dictionary into appropriate object type."""
    # Car object (inside 'car' key)
    if 'make' in dct and 'model' in dct:
        return Car(
            dct['make'],
            dct['model'],
            dct['trim'],
            dct['year'],
            dct['purchaseDate'],
            dct['purchaseMiles'],
        )
    # Rule object
    elif 'item' in dct and 'verb' in dct:
        return Rule(
            dct['item'],
            dct['verb'],
            dct.get('intervalMiles'),
            dct.get('intervalMonths'),
            dct.get('severeIntervalMiles'),
            dct.get('severeIntervalMonths'),
            dct.get('notes'),
            dct.get('phase'),
            dct.get('startMiles'),
            dct.get('stopMiles'),
            dct.get('startMonths'),
            dct.get('stopMonths'),
            dct.get('aftermarket'),
        )
    # History entry
    elif 'ruleKey' in dct:
        return HistoryEntry(
            dct['ruleKey'],
            dct['date'],
            dct.get('mileage'),
            dct.get('performedBy'),
            dct.get('notes'),
            dct.get('cost'),
        )
    # Top-level vehicle object
    elif 'car' in dct and 'rules' in dct:
        state = dct.get('state') or {}
        return Vehicle(
            dct['car'],
            dct['rules'],
            dct.get('history'),
            state.get('asOfDate'),
            state.get('currentMiles'),
        )
    else:
        # Return dict as-is for unknown structures (like 'state')
        return dct


def load_vehicle(filename: str) -> Vehicle:
    """Load a vehicle from a YAML file."""
    with open(filename, 'rb') as fp:
        json_data = json.dumps(yaml.load(fp, Loader=yaml.FullLoader), indent=4)
        return json.loads(json_data, object_hook=_parse_object)


def main():
    parser = argparse.ArgumentParser(
        description="Vehicle maintenance schedule tracker"
    )
    parser.add_argument(
        "vehicle_file",
        type=Path,
        help="Path to vehicle YAML file (e.g., wrx-rules.yaml)"
    )
    args = parser.parse_args()

    if not args.vehicle_file.exists():
        print(f"Error: File not found: {args.vehicle_file}")
        return 1

    vehicle = load_vehicle(args.vehicle_file)

    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {vehicle.current_miles:,.0f} (as of {vehicle.as_of_date})")
    print(f"Rules: {len(vehicle.rules)}")
    print(f"History entries: {len(vehicle.history)}")
    print()

    # Get all service statuses
    statuses = vehicle.get_all_service_status()

    # Group by status
    overdue = [s for s in statuses if s.status == Status.OVERDUE]
    due_soon = [s for s in statuses if s.status == Status.DUE_SOON]
    ok = [s for s in statuses if s.status == Status.OK]
    inactive = [s for s in statuses if s.status == Status.INACTIVE]
    unknown = [s for s in statuses if s.status == Status.UNKNOWN]

    def format_miles(miles: Optional[float]) -> str:
        return f"{miles:,.0f}" if miles is not None else "-"

    def format_remaining(svc: ServiceDue) -> str:
        if svc.miles_remaining is None:
            return "-"
        if svc.miles_remaining < 0:
            return f"-{abs(svc.miles_remaining):,.0f}"
        return f"{svc.miles_remaining:,.0f}"

    def make_table(services: List[ServiceDue]) -> List[List[str]]:
        rows = []
        for svc in services:
            last_done = "-"
            if svc.last_service_date or svc.last_service_miles:
                parts = []
                if svc.last_service_date:
                    parts.append(svc.last_service_date)
                if svc.last_service_miles:
                    parts.append(f"{svc.last_service_miles:,.0f}")
                last_done = " @ ".join(parts)

            rows.append([
                svc.rule.key,
                last_done,
                format_miles(svc.due_miles),
                svc.due_date or "-",
                format_remaining(svc),
                format_miles(svc.severe_due_miles),
            ])
        return rows

    headers = ["Rule", "Last Done", "Due (mi)", "Due (date)", "Remaining", "Severe"]

    if overdue:
        print("OVERDUE:")
        print(tabulate(make_table(overdue), headers=headers, tablefmt="simple"))
        print()

    if due_soon:
        print("DUE SOON:")
        print(tabulate(make_table(due_soon), headers=headers, tablefmt="simple"))
        print()

    if ok:
        print("OK:")
        print(tabulate(make_table(ok), headers=headers, tablefmt="simple"))
        print()

    if unknown:
        print("UNKNOWN (no history):")
        for svc in unknown:
            print(f"  {svc.rule.key}")
        print()

    if inactive:
        print(f"INACTIVE ({len(inactive)} rules not applicable at current mileage)")


if __name__ == '__main__':
    main()
