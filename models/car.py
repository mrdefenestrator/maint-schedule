"""Car class for vehicle identification."""

from typing import Optional


class Car:
    """Vehicle identification and purchase information."""

    def __init__(
        self,
        make: str,
        model: str,
        trim: Optional[str],
        year: int,
        purchase_date: str,
        purchase_miles: float,
    ):
        self.make = make
        self.model = model
        self.trim = trim
        self.year = year
        self.purchase_date = purchase_date
        self.purchase_miles = purchase_miles

    @property
    def name(self) -> str:
        """Human-readable vehicle name."""
        base = f"{self.year} {self.make} {self.model}"
        return f"{base} {self.trim}" if self.trim else base
