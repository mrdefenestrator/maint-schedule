#!/usr/bin/env python3
import json
import yaml
from typing import List
from types import SimpleNamespace


class Rule:
    item: str
    verb: str
    phase: str  # Optional: "initial" or "ongoing" for lifecycle rules
    interval_miles: float
    interval_months: float
    severe_interval_miles: float
    severe_interval_months: float
    notes: str
    start_miles: float = 0
    stop_miles: float = 999999999
    start_months: float = 0
    stop_months: float = 9999
    aftermarket: bool = False

    def __init__(
            self,
            item,
            verb,
            interval_miles,
            interval_months,
            severe_interval_miles,
            severe_interval_months,
            notes,
            phase=None,
            start_miles=0,
            stop_miles=999999999,
            start_months=0,
            stop_months=999,
            aftermarket=False,
    ):
        self.item = item
        self.verb = verb
        self.phase = phase
        self.interval_miles = interval_miles
        self.interval_months = interval_months
        self.severe_interval_miles = severe_interval_miles
        self.severe_interval_months = severe_interval_months
        self.notes = notes
        self.start_miles = start_miles
        self.stop_miles = stop_miles
        self.start_months = start_months
        self.stop_months = stop_months
        self.aftermarket = aftermarket

    @property
    def key(self):
        """Generate natural key from item/verb/phase."""
        base = f"{self.item}/{self.verb}"
        if self.phase:
            return f"{base}/{self.phase}"
        return base


class Car:
    make: str
    model: str
    trim: str
    year: int
    purchase_date: str
    purchase_miles: float

    def __init__(self, make, model, trim, year, purchase_date, purchase_miles):
        self.make = make
        self.model = model
        self.trim = trim
        self.year = year
        self.purchase_date = purchase_date
        self.purchase_miles = purchase_miles


class Ruleset:
    car: Car
    rules: List[Rule]

    def __init__(self, car, rules):
        self.car = car
        self.rules = rules


def as_car(dct):
    if 'make' in dct:
        return Car(
            dct['make'],
            dct['model'],
            dct['trim'],
            dct['year'],
            dct['purchaseDate'],
            dct['purchaseMiles'],
        )
    elif 'item' in dct:
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
    elif 'rules' in dct:
        return Ruleset(
            dct['car'],
            dct['rules'],
        )
    else:
        raise TypeError('unable to determine object type')


def load_yaml_file(filename):
    with open(filename, 'rb') as fp:
        json_data = json.dumps(yaml.load(fp, Loader=yaml.FullLoader), indent=4)
        return json.loads(json_data, object_hook=as_car)


def main():
    # schema = load_yaml_file('schema.yaml')
    car = load_yaml_file('wrx-rules.yaml')

    for rule in car.rules:
        print(f"{rule.key}: {rule.interval_miles} miles / {rule.interval_months} months")


if __name__ == '__main__':
    main()
