"""YAML loading and saving utilities for vehicle data."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from .car import Car
from .rule import Rule
from .history_entry import HistoryEntry
from .vehicle import Vehicle


def _parse_object(dct: Dict[str, Any]) -> Union[Car, Rule, HistoryEntry, Vehicle, dict]:
    """Parse dictionary into appropriate object type."""
    # Car object (inside 'car' key)
    if "make" in dct and "model" in dct:
        return Car(
            dct["make"],
            dct["model"],
            dct.get("trim"),
            dct["year"],
            dct["purchaseDate"],
            dct["purchaseMiles"],
        )
    # Rule object
    elif "item" in dct and "verb" in dct:
        return Rule(
            dct["item"],
            dct["verb"],
            dct.get("intervalMiles"),
            dct.get("intervalMonths"),
            dct.get("severeIntervalMiles"),
            dct.get("severeIntervalMonths"),
            dct.get("notes"),
            dct.get("phase"),
            dct.get("startMiles"),
            dct.get("stopMiles"),
            dct.get("startMonths"),
            dct.get("stopMonths"),
            dct.get("aftermarket"),
        )
    # History entry
    elif "ruleKey" in dct:
        return HistoryEntry(
            dct["ruleKey"],
            dct["date"],
            dct.get("mileage"),
            dct.get("performedBy"),
            dct.get("notes"),
            dct.get("cost"),
        )
    # Top-level vehicle object
    elif "car" in dct and "rules" in dct:
        state = dct.get("state") or {}
        return Vehicle(
            dct["car"],
            dct["rules"],
            dct.get("history"),
            state.get("asOfDate"),
            state.get("currentMiles"),
        )
    else:
        # Return dict as-is for unknown structures (like 'state')
        return dct


def load_vehicle(filename: Union[str, Path]) -> Vehicle:
    """Load a vehicle from a YAML file."""
    with open(filename, "rb") as fp:
        json_data = json.dumps(yaml.load(fp, Loader=yaml.SafeLoader), indent=4)
        return json.loads(json_data, object_hook=_parse_object)


def save_history_entry(filename: Union[str, Path], entry: HistoryEntry) -> None:
    """
    Append a history entry to a vehicle YAML file.

    Loads the raw YAML, appends the entry to the history list,
    and writes back to the file.
    """
    # Load the raw YAML data (not parsed into objects)
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    # Ensure history list exists
    if data.get("history") is None:
        data["history"] = []

    # Build the entry dict, omitting None values for cleaner YAML
    entry_dict = {"ruleKey": entry.rule_key, "date": entry.date}
    if entry.mileage is not None:
        entry_dict["mileage"] = entry.mileage
    if entry.performed_by is not None:
        entry_dict["performedBy"] = entry.performed_by
    if entry.notes is not None:
        entry_dict["notes"] = entry.notes
    if entry.cost is not None:
        entry_dict["cost"] = entry.cost

    # Append the new entry
    data["history"].append(entry_dict)

    # Write back to file
    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def update_history_entry(
    filename: Union[str, Path], index: int, entry: HistoryEntry
) -> None:
    """
    Replace a history entry at the given index in a vehicle YAML file.

    Loads the raw YAML, replaces the entry at history[index],
    and writes back to the file.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    history = data.get("history") or []
    if index < 0 or index >= len(history):
        raise IndexError(f"History index {index} out of range (0..{len(history) - 1})")

    entry_dict = {"ruleKey": entry.rule_key, "date": entry.date}
    if entry.mileage is not None:
        entry_dict["mileage"] = entry.mileage
    if entry.performed_by is not None:
        entry_dict["performedBy"] = entry.performed_by
    if entry.notes is not None:
        entry_dict["notes"] = entry.notes
    if entry.cost is not None:
        entry_dict["cost"] = entry.cost

    history[index] = entry_dict

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def _rule_to_dict(rule: Rule) -> Dict[str, Any]:
    """Serialize a Rule to the YAML dict format (camelCase keys)."""
    d: Dict[str, Any] = {"item": rule.item, "verb": rule.verb}
    if rule.phase is not None:
        d["phase"] = rule.phase
    if rule.interval_miles is not None:
        d["intervalMiles"] = rule.interval_miles
    if rule.interval_months is not None:
        d["intervalMonths"] = rule.interval_months
    if rule.severe_interval_miles is not None:
        d["severeIntervalMiles"] = rule.severe_interval_miles
    if rule.severe_interval_months is not None:
        d["severeIntervalMonths"] = rule.severe_interval_months
    if rule.notes is not None:
        d["notes"] = rule.notes
    if rule.start_miles is not None and rule.start_miles != 0:
        d["startMiles"] = rule.start_miles
    if rule.stop_miles is not None and rule.stop_miles != 999999999:
        d["stopMiles"] = rule.stop_miles
    if rule.start_months is not None and rule.start_months != 0:
        d["startMonths"] = rule.start_months
    if rule.stop_months is not None and rule.stop_months != 9999:
        d["stopMonths"] = rule.stop_months
    if rule.aftermarket:
        d["aftermarket"] = rule.aftermarket
    return d


def add_rule(filename: Union[str, Path], rule: Rule) -> None:
    """
    Append a rule to a vehicle YAML file.

    Loads the raw YAML, appends the rule to the rules list,
    and writes back to the file.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    if data.get("rules") is None:
        data["rules"] = []

    data["rules"].append(_rule_to_dict(rule))

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def update_rule(filename: Union[str, Path], index: int, rule: Rule) -> None:
    """
    Replace a rule at the given index in a vehicle YAML file.

    Loads the raw YAML, replaces the rule at rules[index],
    and writes back to the file.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    rules = data.get("rules") or []
    if index < 0 or index >= len(rules):
        raise IndexError(f"Rule index {index} out of range (0..{len(rules) - 1})")

    rules[index] = _rule_to_dict(rule)

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def delete_rule(filename: Union[str, Path], index: int) -> None:
    """
    Remove a rule at the given index in a vehicle YAML file.

    Loads the raw YAML, removes the rule at rules[index],
    and writes back to the file.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    rules = data.get("rules") or []
    if index < 0 or index >= len(rules):
        raise IndexError(f"Rule index {index} out of range (0..{len(rules) - 1})")

    del rules[index]

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def delete_history_entry(filename: Union[str, Path], index: int) -> None:
    """
    Remove a history entry at the given index in a vehicle YAML file.

    Loads the raw YAML, removes the entry at history[index],
    and writes back to the file.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    history = data.get("history") or []
    if index < 0 or index >= len(history):
        raise IndexError(f"History index {index} out of range (0..{len(history) - 1})")

    del history[index]

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def save_current_miles(filename: Union[str, Path], miles: float) -> None:
    """
    Update the current mileage in the state section of a vehicle YAML file.

    Loads the raw YAML, updates state.currentMiles,
    and writes back to the file.
    """
    # Load the raw YAML data (not parsed into objects)
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    # Ensure state section exists
    if data.get("state") is None:
        data["state"] = {}

    # Update the current miles
    data["state"]["currentMiles"] = miles

    # Write back to file
    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def _car_to_dict(car: Car) -> Dict[str, Any]:
    """Serialize a Car to the YAML dict format (camelCase keys)."""
    d: Dict[str, Any] = {
        "make": car.make,
        "model": car.model,
        "year": car.year,
        "purchaseDate": car.purchase_date,
        "purchaseMiles": car.purchase_miles,
    }
    if car.trim is not None:
        d["trim"] = car.trim
    return d


def create_vehicle(
    filename: Union[str, Path],
    car: Car,
    current_miles: Optional[float] = None,
    as_of_date: Optional[str] = None,
) -> None:
    """
    Create a new vehicle YAML file with the given car and optional state.

    Initializes with empty rules and history.
    """
    data: Dict[str, Any] = {
        "car": _car_to_dict(car),
        "state": {},
        "rules": [],
        "history": [],
    }
    if current_miles is not None:
        data["state"]["currentMiles"] = current_miles
    if as_of_date is not None:
        data["state"]["asOfDate"] = as_of_date
    if not data["state"]:
        data["state"] = {"currentMiles": car.purchase_miles}

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def update_vehicle_meta(
    filename: Union[str, Path],
    car: Optional[Car] = None,
    current_miles: Optional[float] = None,
    as_of_date: Optional[str] = None,
) -> None:
    """
    Update car and/or state (currentMiles, asOfDate) in a vehicle YAML file.

    Only updates fields that are provided (non-None). Leaves other keys unchanged.
    """
    with open(filename, "r") as fp:
        data = yaml.load(fp, Loader=yaml.SafeLoader)

    if car is not None:
        data["car"] = _car_to_dict(car)

    if current_miles is not None or as_of_date is not None:
        if data.get("state") is None:
            data["state"] = {}
        if current_miles is not None:
            data["state"]["currentMiles"] = current_miles
        if as_of_date is not None:
            data["state"]["asOfDate"] = as_of_date

    with open(filename, "w") as fp:
        yaml.dump(
            data,
            fp,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )


def delete_vehicle(filename: Union[str, Path]) -> None:
    """Remove a vehicle YAML file from disk."""
    Path(filename).unlink()
