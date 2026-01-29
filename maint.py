#!/usr/bin/env python3
"""
Unified CLI for vehicle maintenance tracking.

Commands:
  status       - Show what maintenance is due, overdue, or upcoming
  history      - View service history
  log          - Add a new service entry
  update-miles - Update current vehicle mileage
  rules        - List available maintenance rules
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from tabulate import tabulate
from typing import List, Optional

from models import (
    Status,
    ServiceDue,
    HistoryEntry,
    load_vehicle,
    save_history_entry,
    save_current_miles,
)

# =============================================================================
# Formatting helpers
# =============================================================================


def format_miles(miles: Optional[float]) -> str:
    """Format mileage for display."""
    return f"{miles:,.0f}" if miles is not None else "-"


def format_cost(cost: Optional[float]) -> str:
    """Format cost for display."""
    return f"${cost:,.2f}" if cost is not None else "-"


def format_remaining(svc: ServiceDue) -> str:
    """Format remaining miles for display."""
    if svc.miles_remaining is None:
        return "-"
    if svc.miles_remaining < 0:
        return f"-{abs(svc.miles_remaining):,.0f}"
    return f"{svc.miles_remaining:,.0f}"


def format_time_remaining(svc: ServiceDue) -> str:
    """Format remaining time for display (e.g., '3mo 15d' or '-2mo 5d')."""
    if svc.time_remaining_days is None:
        return "-"

    days = svc.time_remaining_days
    if days < 0:
        # Overdue - show as negative
        days = abs(days)
        months = days // 30
        remaining_days = days % 30
        if months > 0:
            return f"-{months}mo {remaining_days}d"
        return f"-{days}d"
    else:
        # Future - show as positive
        months = days // 30
        remaining_days = days % 30
        if months > 0:
            return f"{months}mo {remaining_days}d"
        return f"{days}d"


def truncate(text: Optional[str], max_len: int = 30) -> str:
    """Truncate text with ellipsis if too long."""
    if text is None:
        return "-"
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


# =============================================================================
# Status command
# =============================================================================


def make_status_table(services: List[ServiceDue]) -> List[List[str]]:
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

        rows.append(
            [
                svc.rule.display_name,
                last_done,
                format_miles(svc.due_miles),
                svc.due_date or "-",
                format_remaining(svc),
                format_time_remaining(svc),
            ]
        )
    return rows


def cmd_status(args):
    """Show what maintenance is due, overdue, or upcoming."""
    vehicle = load_vehicle(args.vehicle_file)

    # Validate mutually exclusive flags
    if args.miles_only and args.time_only:
        print("Error: --miles-only and --time-only cannot be used together")
        return 1

    # Parse exclude-verbs
    exclude_verbs = None
    if args.exclude_verbs:
        exclude_verbs = [v.strip() for v in args.exclude_verbs.split(",")]

    # Header
    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {vehicle.current_miles:,.0f} (as of {vehicle.as_of_date})")
    if args.severe:
        print("Mode: SEVERE DRIVING (shorter intervals)")
    if args.miles_only:
        print("Filter: MILEAGE ONLY (ignoring time-based intervals)")
    if args.time_only:
        print("Filter: TIME ONLY (ignoring mileage-based intervals)")
    if exclude_verbs:
        print(f"Filter: EXCLUDING VERBS: {', '.join(exclude_verbs)}")
    print(f"Rules: {len(vehicle.rules)}")
    print(f"History entries: {len(vehicle.history)}")
    print()

    # Get all service statuses
    statuses = vehicle.get_all_service_status(
        severe=args.severe,
        miles_only=args.miles_only,
        time_only=args.time_only,
        exclude_verbs=exclude_verbs,
    )

    # Group by status and sort by item for logical grouping
    overdue = sorted(
        [s for s in statuses if s.status == Status.OVERDUE],
        key=lambda s: (s.rule.item, s.rule.verb, s.rule.phase or ""),
    )
    due_soon = sorted(
        [s for s in statuses if s.status == Status.DUE_SOON],
        key=lambda s: (s.rule.item, s.rule.verb, s.rule.phase or ""),
    )
    ok = sorted(
        [s for s in statuses if s.status == Status.OK],
        key=lambda s: (s.rule.item, s.rule.verb, s.rule.phase or ""),
    )
    inactive = sorted(
        [s for s in statuses if s.status == Status.INACTIVE],
        key=lambda s: (s.rule.item, s.rule.verb, s.rule.phase or ""),
    )
    unknown = sorted(
        [s for s in statuses if s.status == Status.UNKNOWN],
        key=lambda s: (s.rule.item, s.rule.verb, s.rule.phase or ""),
    )

    headers = [
        "Rule",
        "Last Done",
        "Due (mi)",
        "Due (date)",
        "Remaining (mi)",
        "Remaining (time)",
    ]

    if overdue:
        print("OVERDUE:")
        print(tabulate(make_status_table(overdue), headers=headers, tablefmt="simple"))
        print()

    if due_soon:
        print("DUE SOON:")
        print(tabulate(make_status_table(due_soon), headers=headers, tablefmt="simple"))
        print()

    if ok:
        print("OK:")
        print(tabulate(make_status_table(ok), headers=headers, tablefmt="simple"))
        print()

    if unknown:
        print("UNKNOWN (no history):")
        for svc in unknown:
            print(f"  {svc.rule.display_name}")
        print()

    if inactive:
        print(f"INACTIVE ({len(inactive)} rules not applicable at current mileage):")
        for svc in inactive:
            print(f"  {svc.rule.display_name}")
        print()

    return 0


# =============================================================================
# History command
# =============================================================================


def make_history_table(entries: List[HistoryEntry], vehicle) -> List[List[str]]:
    """Convert history entries to table rows."""
    rows = []
    for entry in entries:
        # Find the rule to get display name, fallback to key if not found
        rule = vehicle.get_rule(entry.rule_key)
        display_name = rule.display_name if rule else entry.rule_key

        rows.append(
            [
                entry.date,
                format_miles(entry.mileage),
                display_name,
                entry.performed_by or "-",
                format_cost(entry.cost),
                truncate(entry.notes),
            ]
        )
    return rows


def cmd_history(args):
    """View service history."""
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
    print(
        tabulate(
            make_history_table(entries, vehicle), headers=headers, tablefmt="simple"
        )
    )

    return 0


# =============================================================================
# Log command
# =============================================================================


def cmd_log(args):
    """Add a new service entry."""
    vehicle = load_vehicle(args.vehicle_file)

    # Normalize rule key to lowercase for case-insensitive matching
    normalized_key = args.rule_key.lower()

    # Try to find the rule (case-insensitive)
    rule = None
    for r in vehicle.rules:
        if r.key.lower() == normalized_key:
            rule = r
            break

    if rule is None:
        print(f"Error: Unknown rule key '{args.rule_key}'")
        print("\nAvailable rules:")
        # Sort by item for easier scanning
        sorted_rules = sorted(
            vehicle.rules, key=lambda r: (r.item, r.verb, r.phase or "")
        )
        for r in sorted_rules:
            print(f"  {r.display_name}")
            print(f"    Key: {r.key}")
        return 1

    # Build the entry using the canonical key from the matched rule
    entry_date = args.date or date.today().isoformat()
    entry = HistoryEntry(
        rule_key=rule.key,  # Use canonical key from matched rule
        date=entry_date,
        mileage=args.mileage,
        performed_by=args.by,
        notes=args.notes,
        cost=args.cost,
    )

    # Show what will be added
    print(f"Adding service entry to {args.vehicle_file}:")
    print(f"  Rule:    {rule.display_name}")
    print(f"  Date:    {entry.date}")
    if entry.mileage:
        print(f"  Mileage: {entry.mileage:,.0f}")
    if entry.performed_by:
        print(f"  By:      {entry.performed_by}")
    if entry.notes:
        print(f"  Notes:   {entry.notes}")
    if entry.cost:
        print(f"  Cost:    ${entry.cost:.2f}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    # Save the entry
    save_history_entry(args.vehicle_file, entry)
    print("Entry saved.")

    return 0


# =============================================================================
# Update Miles command
# =============================================================================


def cmd_update_miles(args):
    """Update current vehicle mileage."""
    vehicle = load_vehicle(args.vehicle_file)
    old_miles = vehicle.current_miles

    # Show what will be updated
    print(f"Vehicle: {vehicle.car.name}")
    print(f"Current mileage: {old_miles:,.0f}")
    print(f"New mileage:     {args.mileage:,.0f}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    # Save the new mileage
    save_current_miles(args.vehicle_file, args.mileage)
    print("Mileage updated.")

    return 0


# =============================================================================
# Rules command
# =============================================================================


def cmd_rules(args):
    """List available maintenance rules."""
    vehicle = load_vehicle(args.vehicle_file)

    print(f"Vehicle: {vehicle.car.name}")
    print(f"Rules: {len(vehicle.rules)}")
    print()

    # Sort rules by item, then verb, then phase for logical grouping
    sorted_rules = sorted(vehicle.rules, key=lambda r: (r.item, r.verb, r.phase or ""))

    rows = []
    for rule in sorted_rules:
        interval = []
        if rule.interval_miles:
            interval.append(f"{rule.interval_miles:,.0f} mi")
        if rule.interval_months:
            interval.append(f"{rule.interval_months} mo")
        interval_str = " / ".join(interval) if interval else "-"

        severe = []
        if rule.severe_interval_miles:
            severe.append(f"{rule.severe_interval_miles:,.0f} mi")
        if rule.severe_interval_months:
            severe.append(f"{rule.severe_interval_months} mo")
        severe_str = " / ".join(severe) if severe else "-"

        rows.append([rule.display_name, interval_str, severe_str])

    headers = ["Rule", "Interval", "Severe Interval"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))

    return 0


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Vehicle maintenance tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s vehicles/brz.yaml status
  %(prog)s vehicles/brz.yaml status --severe
  %(prog)s vehicles/brz.yaml status --miles-only
  %(prog)s vehicles/brz.yaml status --exclude-verbs inspect
  %(prog)s vehicles/brz.yaml history --rule "oil"
  %(prog)s vehicles/brz.yaml history --since 2024-01-01
  %(prog)s vehicles/brz.yaml rules
  %(prog)s vehicles/brz.yaml log "engine oil and filter/replace" \\
      --mileage 58000 --by self
  %(prog)s vehicles/brz.yaml update-miles 58000
""",
    )
    parser.add_argument(
        "vehicle_file",
        type=Path,
        help="Path to vehicle YAML file",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Status subcommand
    status_parser = subparsers.add_parser(
        "status", help="Show what maintenance is due, overdue, or upcoming"
    )
    status_parser.add_argument(
        "--severe",
        action="store_true",
        help="Use severe driving intervals (shorter intervals)",
    )
    status_parser.add_argument(
        "--miles-only",
        action="store_true",
        help="Only consider mileage-based intervals (ignore time)",
    )
    status_parser.add_argument(
        "--time-only",
        action="store_true",
        help="Only consider time-based intervals (ignore mileage)",
    )
    status_parser.add_argument(
        "--exclude-verbs",
        type=str,
        help=(
            "Exclude rules with specified verbs "
            '(comma-separated, e.g., "inspect,rotate")'
        ),
    )

    # History subcommand
    history_parser = subparsers.add_parser("history", help="View service history")
    history_parser.add_argument(
        "--rule",
        type=str,
        help="Filter to rules containing text (case-insensitive, e.g., 'oil', 'brake')",
    )
    history_parser.add_argument(
        "--since",
        type=str,
        help="Show only entries since date (YYYY-MM-DD)",
    )
    history_parser.add_argument(
        "--sort",
        choices=["date", "miles", "rule"],
        default="date",
        help="Sort order (default: date)",
    )
    history_parser.add_argument(
        "--asc",
        action="store_true",
        help="Sort ascending instead of descending",
    )

    # Log subcommand
    log_parser = subparsers.add_parser("log", help="Add a new service entry")
    log_parser.add_argument(
        "rule_key",
        type=str,
        help="Rule key (e.g., 'engine oil and filter/replace')",
    )
    log_parser.add_argument(
        "--date",
        type=str,
        help="Service date in YYYY-MM-DD format (default: today)",
    )
    log_parser.add_argument(
        "--mileage",
        type=float,
        help="Mileage at time of service",
    )
    log_parser.add_argument(
        "--by",
        type=str,
        help="Who performed the service (e.g., 'self', 'Dealer')",
    )
    log_parser.add_argument(
        "--notes",
        type=str,
        help="Notes about the service",
    )
    log_parser.add_argument(
        "--cost",
        type=float,
        help="Cost of service",
    )
    log_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without saving",
    )

    # Update Miles subcommand
    update_miles_parser = subparsers.add_parser(
        "update-miles", help="Update current vehicle mileage"
    )
    update_miles_parser.add_argument(
        "mileage",
        type=float,
        help="Current mileage",
    )
    update_miles_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving",
    )

    # Rules subcommand
    subparsers.add_parser("rules", help="List available maintenance rules")

    args = parser.parse_args()

    # Validate vehicle file exists
    if not args.vehicle_file.exists():
        print(f"Error: File not found: {args.vehicle_file}")
        return 1

    # Dispatch to command handler
    if args.command == "status":
        return cmd_status(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "log":
        return cmd_log(args)
    elif args.command == "update-miles":
        return cmd_update_miles(args)
    elif args.command == "rules":
        return cmd_rules(args)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
