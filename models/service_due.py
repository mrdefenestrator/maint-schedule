"""ServiceDue dataclass for calculated service status."""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from .status import Status

if TYPE_CHECKING:
    from .rule import Rule


@dataclass
class ServiceDue:
    """Calculated service due information for a rule."""

    rule: "Rule"
    status: Status
    last_service_miles: Optional[float] = None
    last_service_date: Optional[str] = None
    due_miles: Optional[float] = None
    due_date: Optional[str] = None
    severe_due_miles: Optional[float] = None
    severe_due_date: Optional[str] = None
    miles_remaining: Optional[float] = None
    time_remaining_days: Optional[int] = None

    @property
    def is_due(self) -> bool:
        return self.status in (Status.OVERDUE, Status.DUE_SOON)
