#!/usr/bin/env python3
"""
Unified CLI for vehicle maintenance tracking.

Commands:
  status       - Show what maintenance is due, overdue, or upcoming
  history      - View service history (use --show-index to get indices for edit/delete)
  log          - Add a new service entry
  edit         - Edit an existing history entry by index
  delete       - Delete a history entry by index
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
    update_history_entry,
    delete_history_entry,
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

    # Column alignment: left, left, right, left, right, right
    colalign = ("left", "left", "right", "left", "right", "right")

    if overdue:
        print("OVERDUE:")
        print(
            tabulate(
                make_status_table(overdue),
                headers=headers,
                tablefmt="simple",
                colalign=colalign,
            )
        )
        print()

    if due_soon:
        print("DUE SOON:")
        print(
            tabulate(
                make_status_table(due_soon),
                headers=headers,
                tablefmt="simple",
                colalign=colalign,
            )
        )
        print()

    if ok:
        print("OK:")
        print(
            tabulate(
                make_status_table(ok),
                headers=headers,
                tablefmt="simple",
                colalign=colalign,
            )
        )
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


def make_history_table(
    entries: List[HistoryEntry], vehicle, show_index: bool = False, indices=None
) -> List[List[str]]:
    """Convert history entries to table rows. If show_index, first column is index (indices required)."""
    rows = []
    for i, entry in enumerate(entries):
        # Find the rule to get display name, fallback to key if not found
        rule = vehicle.get_rule(entry.rule_key)
        display_name = rule.display_name if rule else entry.rule_key

        row = [
            entry.date,
            format_miles(entry.mileage),
            display_name,
            entry.performed_by or "-",
            format_cost(entry.cost),
            truncate(entry.notes),
        ]
        if show_index and indices is not None:
            row.insert(0, str(indices[i]))
        rows.append(row)
    return rows


def cmd_history(args):
    """View service history."""
    vehicle = load_vehicle(args.vehicle_file)

    # Build (raw_index, entry) and sort like get_history_sorted for consistent order
    if args.sort == "date":
        key_fn = lambda ie: ie[1].date
    elif args.sort == "miles":
        key_fn = lambda ie: ie[1].mileage or 0
    else:
        key_fn = lambda ie: (ie[1].rule_key, ie[1].date)

    entries_with_index = sorted(
        enumerate(vehicle.history), key=key_fn, reverse=not args.asc
    )
    indices = [ie[0] for ie in entries_with_index]
    entries = [ie[1] for ie in entries_with_index]

    # Apply filters
    if args.rule:
        filtered = [
            (i, e) for i, e in zip(indices, entries) if args.rule.lower() in e.rule_key.lower()
        ]
        indices = [f[0] for f in filtered]
        entries = [f[1] for f in filtered]

    if args.since:
        filtered = [(i, e) for i, e in zip(indices, entries) if e.date >= args.since]
        indices = [f[0] for f in filtered]
        entries = [f[1] for f in filtered]

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
    if args.show_index:
        print("Index column is for: maint edit/delete <file> <index> ...")
    print()

    if not entries:
        print("No history entries found.")
        return 0

    headers = ["Date", "Mileage", "Rule", "Performed By", "Cost", "Notes"]
    colalign = ("left", "right", "left", "left", "right", "left")
    if args.show_index:
        headers.insert(0, "Index")
        colalign = ("right",) + colalign

    print(
        tabulate(
            make_history_table(entries, vehicle, show_index=args.show_index, indices=indices),
            headers=headers,
            tablefmt="simple",
            colalign=colalign,
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
# Edit command
# =============================================================================


def cmd_edit(args):
    """Edit an existing history entry by index."""
    vehicle = load_vehicle(args.vehicle_file)

    if args.index < 0 or args.index >= len(vehicle.history):
        print(f"Error: Index {args.index} out of range (0..{len(vehicle.history) - 1})")
        return 1

    existing = vehicle.history[args.index]

    # Build updated entry: only override fields that were explicitly passed
    if args.rule_key is not None:
        normalized_key = args.rule_key.lower()
        rule = None
        for r in vehicle.rules:
            if r.key.lower() == normalized_key:
                rule = r
                break
        if rule is None:
            print(f"Error: Unknown rule key '{args.rule_key}'")
            return 1
        rule_key = rule.key
        rule_display = rule.display_name
    else:
        rule_key = existing.rule_key
        rule = vehicle.get_rule(existing.rule_key)
        rule_display = rule.display_name if rule else existing.rule_key

    entry_date = args.date if args.date is not None else existing.date
    mileage = args.mileage if args.mileage is not None else existing.mileage
    performed_by = args.by if args.by is not None else existing.performed_by
    notes = args.notes if args.notes is not None else existing.notes
    cost = args.cost if args.cost is not None else existing.cost

    entry = HistoryEntry(
        rule_key=rule.key,
        date=entry_date,
        mileage=mileage,
        performed_by=performed_by,
        notes=notes,
        cost=cost,
    )

    print(f"Updating history entry {args.index} in {args.vehicle_file}:")
    print(f"  Rule:    {rule_display}")
    print(f"  Date:    {entry.date}")
    if entry.mileage is not None:
        print(f"  Mileage: {entry.mileage:,.0f}")
    if entry.performed_by:
        print(f"  By:      {entry.performed_by}")
    if entry.notes:
        print(f"  Notes:   {entry.notes}")
    if entry.cost is not None:
        print(f"  Cost:    ${entry.cost:.2f}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    try:
        update_history_entry(args.vehicle_file, args.index, entry)
    except IndexError as e:
        print(f"Error: {e}")
        return 1
    print("Entry updated.")
    return 0


# =============================================================================
# Delete command
# =============================================================================


def cmd_delete(args):
    """Delete a history entry by index."""
    vehicle = load_vehicle(args.vehicle_file)

    if args.index < 0 or args.index >= len(vehicle.history):
        print(f"Error: Index {args.index} out of range (0..{len(vehicle.history) - 1})")
        return 1

    entry = vehicle.history[args.index]
    rule = vehicle.get_rule(entry.rule_key)
    display_name = rule.display_name if rule else entry.rule_key

    print(f"Deleting history entry {args.index} from {args.vehicle_file}:")
    print(f"  {entry.date}  {display_name}")
    if entry.mileage:
        print(f"  Mileage: {entry.mileage:,.0f}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    try:
        delete_history_entry(args.vehicle_file, args.index)
    except IndexError as e:
        print(f"Error: {e}")
        return 1
    print("Entry deleted.")
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
        # Format interval miles
        interval_miles = f"{rule.interval_miles:,.0f}" if rule.interval_miles else "-"

        # Format interval time
        interval_time = f"{rule.interval_months} mo" if rule.interval_months else "-"

        # Format severe interval miles
        severe_miles = (
            f"{rule.severe_interval_miles:,.0f}" if rule.severe_interval_miles else "-"
        )

        # Format severe interval time
        severe_time = (
            f"{rule.severe_interval_months} mo" if rule.severe_interval_months else "-"
        )

        rows.append(
            [
                rule.display_name,
                interval_miles,
                interval_time,
                severe_miles,
                severe_time,
            ]
        )

    headers = [
        "Rule",
        "Interval (mi)",
        "Interval (time)",
        "Severe (mi)",
        "Severe (time)",
    ]

    # Column alignment: left, right, right, right, right
    colalign = ("left", "right", "right", "right", "right")

    print(tabulate(rows, headers=headers, tablefmt="simple", colalign=colalign))

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
  %(prog)s vehicles/brz.yaml history --show-index
  %(prog)s vehicles/brz.yaml edit 0 --date 2024-01-15 --notes "Corrected date"
  %(prog)s vehicles/brz.yaml delete 0 --dry-run
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
    history_parser.add_argument(
        "--show-index",
        action="store_true",
        help="Show index column for use with: maint edit/delete <file> <index> ...",
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

    # Edit subcommand
    edit_parser = subparsers.add_parser("edit", help="Edit an existing history entry by index")
    edit_parser.add_argument(
        "index",
        type=int,
        help="History entry index (from: maint history --show-index)",
    )
    edit_parser.add_argument(
        "--rule-key",
        type=str,
        help="Rule key (e.g., 'engine oil and filter/replace')",
    )
    edit_parser.add_argument(
        "--date",
        type=str,
        help="Service date in YYYY-MM-DD format",
    )
    edit_parser.add_argument(
        "--mileage",
        type=float,
        help="Mileage at time of service",
    )
    edit_parser.add_argument(
        "--by",
        type=str,
        help="Who performed the service (e.g., 'self', 'Dealer')",
    )
    edit_parser.add_argument(
        "--notes",
        type=str,
        help="Notes about the service",
    )
    edit_parser.add_argument(
        "--cost",
        type=float,
        help="Cost of service",
    )
    edit_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving",
    )

    # Delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a history entry by index")
    delete_parser.add_argument(
        "index",
        type=int,
        help="History entry index (from: maint history --show-index)",
    )
    delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without saving",
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
    elif args.command == "edit":
        return cmd_edit(args)
    elif args.command == "delete":
        return cmd_delete(args)
    elif args.command == "update-miles":
        return cmd_update_miles(args)
    elif args.command == "rules":
        return cmd_rules(args)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
