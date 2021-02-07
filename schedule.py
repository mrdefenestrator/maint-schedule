#!/usr/bin/env python3
import yaml
from typing import List


class Rule:
    item: str
    verb: str
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
            self, item, verb, interval_miles, interval_months, severe_interval_miles, severe_interval_months, notes,
            start_miles, stop_miles, start_months, stop_months, aftermarket
    ):
        self.item = item
        self.verb = verb
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


class Car:
    make: str
    model: str
    trim: str
    year: int
    purchase_date: str
    purchase_miles: float
    rules: List[Rule]

    def __init__(self, make, model, trim, year, purchase_date, purchase_miles, rules):
        self.make = make
        self.model = model
        self.trim = trim
        self.year = year
        self.purchase_date = purchase_date
        self.purchase_miles = purchase_miles
        self.rules = rules


def as_rule(dct):
    return Rule(
        dct['item'],
        dct['verb'],
        dct['intervalMiles'],
        dct['intervalMonths'],
        dct['severeIntervalMiles'],
        dct['severeIntervalMonths'],
        dct['notes'],
        dct['startMiles'],
        dct['stopMiles'],
        dct['startMonths'],
        dct['stopMonths'],
        dct['aftermarket'],
    )


def as_car(dct):
    rules = [as_rule(_) for _ in dct['rules']]
    car = Car(
        dct['make'],
        dct['model'],
        dct['trim'],
        dct['year'],
        dct['purchaseDate'],
        dct['purchaseMiles'],
        rules,
    )
    return car


def load_yaml_file(filename):
    with open(filename, 'rb') as fp:
        return yaml.load(fp, Loader=yaml.FullLoader, object_hook=as_car)


def main():
    # schema = load_yaml_file('schema.yml')
    car = load_yaml_file('wrx-rules.yml')

    for rule in car['rules']:
        print(rule['verb'], rule['item'], rule['intervalMiles'])

    for x in range(10):
        print(car.rules[0].interval_miles * x)


if __name__ == '__main__':
    main()
