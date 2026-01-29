"""
Vehicle maintenance tracking models.

This package provides data models for tracking vehicle maintenance:
- Status: Urgency levels (OVERDUE, DUE_SOON, OK, etc.)
- Rule: Maintenance interval definitions
- Car: Vehicle identification
- HistoryEntry: Service records
- ServiceDue: Calculated service status
- Vehicle: Main aggregate combining all data
"""

from .status import Status
from .car import Car
from .rule import Rule
from .history_entry import HistoryEntry
from .service_due import ServiceDue
from .vehicle import Vehicle
from .calculations import calc_due_miles, calc_due_date, check_status
from .loader import load_vehicle, save_history_entry

__all__ = [
    "Status",
    "Car",
    "Rule",
    "HistoryEntry",
    "ServiceDue",
    "Vehicle",
    "calc_due_miles",
    "calc_due_date",
    "check_status",
    "load_vehicle",
    "save_history_entry",
]
