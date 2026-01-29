"""YAML loading utilities for vehicle data."""
import json
import yaml

from .car import Car
from .rule import Rule
from .history_entry import HistoryEntry
from .vehicle import Vehicle


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
