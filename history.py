#!/usr/bin/env python3
"""
CLI for viewing vehicle maintenance history.

Shows all recorded maintenance services with date, mileage,
who performed the work, cost, and notes.
"""

import argparse
from pathlib import Path
from tabulate import tabulate
from typing import List, Optional

from models import HistoryEntry, load_vehicle


def format_miles(miles: Optional[float]) -> str:
    """Format mileage for display."""
    return f"{miles:,.0f}" if miles is not None else "-"


def format_cost(cost: Optional[float]) -> str:
    """Format cost for display."""
    return f"${cost:,.2f}" if cost is not None else "-"


def truncate(text: Optional[str], max_len: int = 30) -> str:
    """Truncate text with ellipsis if too long."""
    if text is None:
        return "-"
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def make_table(entries: List[HistoryEntry]) -> List[List[str]]:
    """Convert history entries to table rows."""
    rows = []
    for entry in entries:
        rows.append(
            [
                entry.date,
                format_miles(entry.mileage),
                entry.rule_key,
                entry.performed_by or "-",
                format_cost(entry.cost),
                truncate(entry.notes),
            ]
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Vehicle maintenance history viewer")
    parser.add_argument(
        "vehicle_file",
        type=Path,
        help="Path to vehicle YAML file (e.g., wrx-rules.yaml)",
    )
    parser.add_argument(
        "--rule",
        type=str,
        help="Filter to specific rule key (e.g., 'engine oil and filter/replace')",
    )
    parser.add_argument(
        "--since", type=str, help="Show only entries since date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--sort",
        choices=["date", "miles", "rule"],
        default="date",
        help="Sort order (default: date)",
    )
    parser.add_argument(
        "--asc", action="store_true", help="Sort ascending instead of descending"
    )
    args = parser.parse_args()

    if not args.vehicle_file.exists():
        print(f"Error: File not found: {args.vehicle_file}")
        return 1

    vehicle = load_vehicle(args.vehicle_file)

    # Get and sort history
    entries = vehicle.get_history_sorted(sort_by=args.sort, reverse=not args.asc)

    # Apply filters
    if args.rule:
        entries = [e for e in entries if args.rule.lower() in e.rule_key.lower()]

    if args.since:
        entries = [e for e in entries if e.date >= args.since]

    # Calculate summary stats
    total_cost = sum(e.cost for e in entries if e.cost is not None)

    # Get last service info
    last_svc = vehicle.last_service

    # Header
    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {vehicle.current_miles:,.0f} (as of {vehicle.as_of_date})")
    if last_svc:
        last_info = f"{last_svc.date}"
        if last_svc.mileage:
            last_info += f" @ {last_svc.mileage:,.0f} mi"
        print(f"Last service: {last_info}")
    print(f"Total services: {len(vehicle.history)}")
    if args.rule or args.since:
        print(f"Showing: {len(entries)} (filtered)")
    if total_cost > 0:
        print(f"Total cost: ${total_cost:,.2f}")
    print()

    if not entries:
        print("No history entries found.")
        return 0

    headers = ["Date", "Mileage", "Rule", "Performed By", "Cost", "Notes"]
    print(tabulate(make_table(entries), headers=headers, tablefmt="simple"))


if __name__ == "__main__":
    main()
