"""YAML loading and saving utilities for vehicle data."""

import json
from pathlib import Path
from typing import Any, Dict, Union

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
