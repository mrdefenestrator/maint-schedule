#!/usr/bin/env python3
"""Tests for Car class."""

from models import Car


class TestCar:
    """Tests for Car class."""

    def test_name_property(self):
        """Name property returns formatted vehicle name."""
        car = Car("Subaru", "WRX", "Limited", 2012, "2012-03-23", 6)
        assert car.name == "2012 Subaru WRX Limited"

    def test_attributes(self):
        """All attributes are stored correctly."""
        car = Car("Toyota", "Camry", "XLE", 2020, "2020-06-15", 15)
        assert car.make == "Toyota"
        assert car.model == "Camry"
        assert car.trim == "XLE"
        assert car.year == 2020
        assert car.purchase_date == "2020-06-15"
        assert car.purchase_miles == 15

    def test_name_without_trim(self):
        """Name omits trim when trim is None or empty."""
        car_none = Car("Honda", "CBR600RR", None, 2024, "2024-01-01", 0)
        assert car_none.name == "2024 Honda CBR600RR"
        car_empty = Car("Honda", "CBR600RR", "", 2024, "2024-01-01", 0)
        assert car_empty.name == "2024 Honda CBR600RR"
