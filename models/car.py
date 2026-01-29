"""Car class for vehicle identification."""


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
