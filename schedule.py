#!/usr/bin/env python3
"""
CLI for viewing vehicle maintenance schedule status.

Shows what maintenance is due, overdue, or upcoming based on
the vehicle's maintenance rules and service history.
"""
import argparse
from pathlib import Path
from tabulate import tabulate
from typing import List, Optional

from models import Status, ServiceDue, load_vehicle


def format_miles(miles: Optional[float]) -> str:
    """Format mileage for display."""
    return f"{miles:,.0f}" if miles is not None else "-"


def format_remaining(svc: ServiceDue) -> str:
    """Format remaining miles for display."""
    if svc.miles_remaining is None:
        return "-"
    if svc.miles_remaining < 0:
        return f"-{abs(svc.miles_remaining):,.0f}"
    return f"{svc.miles_remaining:,.0f}"


def make_table(services: List[ServiceDue]) -> List[List[str]]:
    """Convert service status list to table rows."""
    rows = []
    for svc in services:
        last_done = "-"
        if svc.last_service_date or svc.last_service_miles:
            parts = []
            if svc.last_service_date:
                parts.append(svc.last_service_date)
            if svc.last_service_miles:
                parts.append(f"{svc.last_service_miles:,.0f}")
            last_done = " @ ".join(parts)

        rows.append([
            svc.rule.key,
            last_done,
            format_miles(svc.due_miles),
            svc.due_date or "-",
            format_remaining(svc),
        ])
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Vehicle maintenance schedule tracker"
    )
    parser.add_argument(
        "vehicle_file",
        type=Path,
        help="Path to vehicle YAML file (e.g., wrx-rules.yaml)"
    )
    parser.add_argument(
        "--severe",
        action="store_true",
        help="Use severe driving intervals (shorter intervals for demanding conditions)"
    )
    args = parser.parse_args()

    if not args.vehicle_file.exists():
        print(f"Error: File not found: {args.vehicle_file}")
        return 1

    vehicle = load_vehicle(args.vehicle_file)

    # Header
    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {vehicle.current_miles:,.0f} (as of {vehicle.as_of_date})")
    if args.severe:
        print("Mode: SEVERE DRIVING (shorter intervals)")
    print(f"Rules: {len(vehicle.rules)}")
    print(f"History entries: {len(vehicle.history)}")
    print()

    # Get all service statuses
    statuses = vehicle.get_all_service_status(severe=args.severe)

    # Group by status
    overdue = [s for s in statuses if s.status == Status.OVERDUE]
    due_soon = [s for s in statuses if s.status == Status.DUE_SOON]
    ok = [s for s in statuses if s.status == Status.OK]
    inactive = [s for s in statuses if s.status == Status.INACTIVE]
    unknown = [s for s in statuses if s.status == Status.UNKNOWN]

    headers = ["Rule", "Last Done", "Due (mi)", "Due (date)", "Remaining"]

    if overdue:
        print("OVERDUE:")
        print(tabulate(make_table(overdue), headers=headers, tablefmt="simple"))
        print()

    if due_soon:
        print("DUE SOON:")
        print(tabulate(make_table(due_soon), headers=headers, tablefmt="simple"))
        print()

    if ok:
        print("OK:")
        print(tabulate(make_table(ok), headers=headers, tablefmt="simple"))
        print()

    if unknown:
        print("UNKNOWN (no history):")
        for svc in unknown:
            print(f"  {svc.rule.key}")
        print()

    if inactive:
        print(f"INACTIVE ({len(inactive)} rules not applicable at current mileage)")


if __name__ == '__main__':
    main()
