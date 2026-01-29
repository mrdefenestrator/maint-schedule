#!/usr/bin/env python3
import json
import yaml
from datetime import date
from typing import List, Optional


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
    vehicle = load_vehicle('wrx-rules.yaml')

    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {vehicle.current_miles} (as of {vehicle.as_of_date})")
    print(f"Rules: {len(vehicle.rules)}")
    print(f"History entries: {len(vehicle.history)}")
    print()

    print("Maintenance Schedule:")
    print("-" * 60)
    for rule in vehicle.rules:
        interval = []
        if rule.interval_miles:
            interval.append(f"{rule.interval_miles:,.0f} mi")
        if rule.interval_months:
            interval.append(f"{rule.interval_months} mo")
        print(f"  {rule.key}: {' / '.join(interval)}")


if __name__ == '__main__':
    main()
