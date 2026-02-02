#!/usr/bin/env python3
"""
Unified CLI for vehicle maintenance tracking.

Commands:
  status  - Show what maintenance is due, overdue, or upcoming
  history - View service history (default); subcommands: add, edit, delete
  add     - Create a new vehicle file
  edit    - Edit vehicle info and/or current mileage
  delete  - Delete the vehicle file
  rules   - List maintenance rules (default); subcommands: add, edit, delete
"""

import argparse
import sys
from datetime import date
from pathlib import Path
from tabulate import tabulate
from typing import List, Optional

from models import (
    Car,
    Status,
    ServiceDue,
    HistoryEntry,
    Rule,
    load_vehicle,
    save_history_entry,
    save_current_miles,
    update_history_entry,
    delete_history_entry,
    add_rule,
    update_rule,
    delete_rule,
    create_vehicle,
    update_vehicle_meta,
    delete_vehicle,
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
        print("Index column is for: maint history edit/delete <index> ...")
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
# Edit-rule command
# =============================================================================


def cmd_edit_rule(args):
    """Edit an existing rule by index."""
    vehicle = load_vehicle(args.vehicle_file)

    if args.index < 0 or args.index >= len(vehicle.rules):
        print(f"Error: Index {args.index} out of range (0..{len(vehicle.rules) - 1})")
        return 1

    existing = vehicle.rules[args.index]

    def _ov(name, val):
        return val if val is not None else getattr(existing, name)

    # aftermarket: only override if explicitly set (--set-aftermarket true/false)
    aftermarket = existing.aftermarket
    if args.set_aftermarket is not None:
        aftermarket = args.set_aftermarket.lower() == "true"

    rule = Rule(
        item=_ov("item", args.item),
        verb=_ov("verb", args.verb),
        interval_miles=_ov("interval_miles", args.interval_miles),
        interval_months=_ov("interval_months", args.interval_months),
        severe_interval_miles=_ov("severe_interval_miles", args.severe_interval_miles),
        severe_interval_months=_ov("severe_interval_months", args.severe_interval_months),
        notes=_ov("notes", args.notes),
        phase=_ov("phase", args.phase),
        start_miles=_ov("start_miles", args.start_miles),
        stop_miles=_ov("stop_miles", args.stop_miles),
        start_months=_ov("start_months", args.start_months),
        stop_months=_ov("stop_months", args.stop_months),
        aftermarket=aftermarket,
    )

    print(f"Updating rule {args.index} in {args.vehicle_file}:")
    print(f"  {rule.display_name}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    try:
        update_rule(args.vehicle_file, args.index, rule)
    except IndexError as e:
        print(f"Error: {e}")
        return 1
    print("Rule updated.")
    return 0


# =============================================================================
# Delete-rule command
# =============================================================================


def cmd_delete_rule(args):
    """Delete a rule by index."""
    vehicle = load_vehicle(args.vehicle_file)

    if args.index < 0 or args.index >= len(vehicle.rules):
        print(f"Error: Index {args.index} out of range (0..{len(vehicle.rules) - 1})")
        return 1

    rule = vehicle.rules[args.index]

    print(f"Deleting rule {args.index} from {args.vehicle_file}:")
    print(f"  {rule.display_name}")
    print(f"  Key: {rule.key}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    try:
        delete_rule(args.vehicle_file, args.index)
    except IndexError as e:
        print(f"Error: {e}")
        return 1
    print("Rule deleted.")
    return 0


# =============================================================================
# Rules add command
# =============================================================================


def cmd_rules_add(args):
    """Add a new rule."""
    vehicle = load_vehicle(args.vehicle_file)

    # Validate item/verb
    item = args.item.strip()
    verb = args.verb.strip()
    if not item or not verb:
        print("Error: --item and --verb are required")
        return 1

    aftermarket = False
    if args.set_aftermarket is not None:
        aftermarket = args.set_aftermarket.lower() == "true"

    rule = Rule(
        item=item,
        verb=verb,
        phase=args.phase or None,
        interval_miles=args.interval_miles,
        interval_months=args.interval_months,
        severe_interval_miles=args.severe_interval_miles,
        severe_interval_months=args.severe_interval_months,
        notes=args.notes or None,
        start_miles=args.start_miles if args.start_miles is not None else 0,
        stop_miles=args.stop_miles if args.stop_miles is not None else 999999999,
        start_months=args.start_months if args.start_months is not None else 0,
        stop_months=args.stop_months if args.stop_months is not None else 9999,
        aftermarket=aftermarket,
    )

    print(f"Adding rule to {args.vehicle_file}:")
    print(f"  {rule.display_name}")
    if rule.interval_miles or rule.interval_months:
        parts = []
        if rule.interval_miles:
            parts.append(f"{rule.interval_miles:,.0f} mi")
        if rule.interval_months:
            parts.append(f"{rule.interval_months:.0f} mo")
        print(f"  Interval: {' / '.join(parts)}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    try:
        add_rule(args.vehicle_file, rule)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    print("Rule added.")
    return 0


# =============================================================================
# Vehicle create / edit / delete
# =============================================================================


def cmd_vehicle_create(args):
    """Create a new vehicle file."""
    car = Car(
        make=args.make.strip(),
        model=args.model.strip(),
        trim=args.trim.strip() if args.trim else None,
        year=int(args.year),
        purchase_date=args.purchase_date,
        purchase_miles=float(args.purchase_miles),
    )

    current_miles = float(args.current_miles) if args.current_miles is not None else None
    as_of_date = args.as_of_date

    print(f"Creating vehicle file: {args.vehicle_file}")
    print(f"  {car.name}")
    print(f"  Purchase: {car.purchase_date} @ {car.purchase_miles:,.0f} mi")
    if current_miles is not None:
        print(f"  Current mileage: {current_miles:,.0f}" + (f" (as of {as_of_date})" if as_of_date else ""))
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    create_vehicle(args.vehicle_file, car, current_miles=current_miles, as_of_date=as_of_date)
    print("Vehicle created.")
    return 0


def cmd_vehicle_edit(args):
    """Edit an existing vehicle (car info and/or current mileage)."""
    vehicle = load_vehicle(args.vehicle_file)

    car = None
    if any(
        (
            args.make is not None,
            args.model is not None,
            args.trim is not None,
            args.year is not None,
            args.purchase_date is not None,
            args.purchase_miles is not None,
        )
    ):
        car = Car(
            make=args.make.strip() if args.make is not None else vehicle.car.make,
            model=args.model.strip() if args.model is not None else vehicle.car.model,
            trim=(args.trim.strip() if args.trim else None) if args.trim is not None else vehicle.car.trim,
            year=int(args.year) if args.year is not None else vehicle.car.year,
            purchase_date=args.purchase_date if args.purchase_date is not None else vehicle.car.purchase_date,
            purchase_miles=float(args.purchase_miles) if args.purchase_miles is not None else vehicle.car.purchase_miles,
        )

    current_miles = float(args.current_miles) if args.current_miles is not None else None
    as_of_date = args.as_of_date

    print(f"Updating vehicle: {args.vehicle_file}")
    if car:
        print(f"  Car: {car.name}")
    if current_miles is not None:
        print(f"  Current mileage: {current_miles:,.0f}" + (f" (as of {as_of_date})" if as_of_date else ""))
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    update_vehicle_meta(
        args.vehicle_file,
        car=car,
        current_miles=current_miles,
        as_of_date=as_of_date,
    )
    print("Vehicle updated.")
    return 0


def cmd_vehicle_delete(args):
    """Delete a vehicle file."""
    vehicle = load_vehicle(args.vehicle_file)

    print(f"Deleting vehicle file: {args.vehicle_file}")
    print(f"  {vehicle.car.name}")
    print()

    if args.dry_run:
        print("(dry run - no changes made)")
        return 0

    if not args.force:
        print("Use --force to confirm deletion.")
        return 1

    delete_vehicle(args.vehicle_file)
    print("Vehicle deleted.")
    return 0


# =============================================================================
# Rules command
# =============================================================================


def cmd_rules(args):
    """List available maintenance rules."""
    vehicle = load_vehicle(args.vehicle_file)

    print(f"Vehicle: {vehicle.car.name}")
    print(f"Rules: {len(vehicle.rules)}")
    if args.show_index:
        print("Index column is for: maint rules edit/delete <index> ...")
    print()

    # Sort rules by item, then verb, then phase; keep (raw_index, rule)
    indexed = list(enumerate(vehicle.rules))
    sorted_indexed = sorted(
        indexed, key=lambda ir: (ir[1].item, ir[1].verb, ir[1].phase or "")
    )
    indices = [ir[0] for ir in sorted_indexed]
    sorted_rules = [ir[1] for ir in sorted_indexed]

    rows = []
    for rule in sorted_rules:
        interval_miles = f"{rule.interval_miles:,.0f}" if rule.interval_miles else "-"
        interval_time = f"{rule.interval_months} mo" if rule.interval_months else "-"
        severe_miles = (
            f"{rule.severe_interval_miles:,.0f}" if rule.severe_interval_miles else "-"
        )
        severe_time = (
            f"{rule.severe_interval_months} mo" if rule.severe_interval_months else "-"
        )
        row = [rule.display_name, interval_miles, interval_time, severe_miles, severe_time]
        if args.show_index:
            row.insert(0, str(indices[len(rows)]))
        rows.append(row)

    headers = ["Rule", "Interval (mi)", "Interval (time)", "Severe (mi)", "Severe (time)"]
    colalign = ("left", "right", "right", "right", "right")
    if args.show_index:
        headers.insert(0, "Index")
        colalign = ("right",) + colalign

    print(tabulate(rows, headers=headers, tablefmt="simple", colalign=colalign))

    return 0


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Vehicle maintenance tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "vehicle_file",
        type=Path,
        help="Path to vehicle YAML file (for create: path for new file; for others: existing file)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Status subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Show what maintenance is due, overdue, or upcoming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml status
  %(prog)s vehicles/brz.yaml status --severe
  %(prog)s vehicles/brz.yaml status --miles-only
  %(prog)s vehicles/brz.yaml status --exclude-verbs inspect
""",
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

    # History subcommand (with nested edit/delete)
    history_parser = subparsers.add_parser(
        "history",
        help="View or modify service history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml history
  %(prog)s vehicles/brz.yaml history --rule "oil"
  %(prog)s vehicles/brz.yaml history --since 2024-01-01
  %(prog)s vehicles/brz.yaml history --show-index
""",
    )
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
        help="Show index column for use with: maint history edit/delete <index> ...",
    )
    history_sub = history_parser.add_subparsers(dest="history_command", required=False)
    history_add_parser = history_sub.add_parser(
        "add",
        help="Add a new service entry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml history add "engine oil and filter/replace" --mileage 58000 --by self
  %(prog)s vehicles/brz.yaml history add "tires/rotate" --mileage 95000 --cost 25.00 --dry-run
""",
    )
    history_add_parser.add_argument(
        "rule_key",
        type=str,
        help="Rule key (e.g., 'engine oil and filter/replace')",
    )
    history_add_parser.add_argument(
        "--date",
        type=str,
        help="Service date in YYYY-MM-DD format (default: today)",
    )
    history_add_parser.add_argument(
        "--mileage",
        type=float,
        help="Mileage at time of service",
    )
    history_add_parser.add_argument(
        "--by",
        type=str,
        help="Who performed the service (e.g., 'self', 'Dealer')",
    )
    history_add_parser.add_argument(
        "--notes",
        type=str,
        help="Notes about the service",
    )
    history_add_parser.add_argument(
        "--cost",
        type=float,
        help="Cost of service",
    )
    history_add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without saving",
    )
    history_edit_parser = history_sub.add_parser(
        "edit",
        help="Edit a history entry by index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml history edit 0 --date 2024-01-15 --notes "Corrected date"
  %(prog)s vehicles/brz.yaml history edit 0 --mileage 58100 --dry-run
""",
    )
    history_edit_parser.add_argument(
        "index",
        type=int,
        help="History entry index (from: maint history --show-index)",
    )
    history_edit_parser.add_argument(
        "--rule-key",
        type=str,
        help="Rule key (e.g., 'engine oil and filter/replace')",
    )
    history_edit_parser.add_argument(
        "--date",
        type=str,
        help="Service date in YYYY-MM-DD format",
    )
    history_edit_parser.add_argument(
        "--mileage",
        type=float,
        help="Mileage at time of service",
    )
    history_edit_parser.add_argument(
        "--by",
        type=str,
        help="Who performed the service (e.g., 'self', 'Dealer')",
    )
    history_edit_parser.add_argument(
        "--notes",
        type=str,
        help="Notes about the service",
    )
    history_edit_parser.add_argument(
        "--cost",
        type=float,
        help="Cost of service",
    )
    history_edit_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving",
    )
    history_delete_parser = history_sub.add_parser(
        "delete",
        help="Delete a history entry by index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml history delete 0
  %(prog)s vehicles/brz.yaml history delete 0 --dry-run
""",
    )
    history_delete_parser.add_argument(
        "index",
        type=int,
        help="History entry index (from: maint history --show-index)",
    )
    history_delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without saving",
    )

    # Add (create vehicle file)
    add_parser = subparsers.add_parser(
        "add",
        help="Create a new vehicle file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/newcar.yaml add --make Subaru --model BRZ --year 2015 --purchase-date 2016-11-12 --purchase-miles 21216
  %(prog)s vehicles/newcar.yaml add --make Subaru --model BRZ --year 2015 --purchase-date 2016-11-12 --purchase-miles 21216 --current-miles 60000 --dry-run
""",
    )
    add_parser.add_argument("--make", type=str, required=True, help="Make (e.g., Subaru)")
    add_parser.add_argument("--model", type=str, required=True, help="Model (e.g., BRZ)")
    add_parser.add_argument("--trim", type=str, help="Trim (optional)")
    add_parser.add_argument("--year", type=int, required=True, help="Year")
    add_parser.add_argument(
        "--purchase-date",
        type=str,
        required=True,
        help="Purchase date (YYYY-MM-DD)",
    )
    add_parser.add_argument(
        "--purchase-miles",
        type=float,
        required=True,
        help="Mileage at purchase",
    )
    add_parser.add_argument(
        "--current-miles",
        type=float,
        help="Current mileage (default: purchase miles)",
    )
    add_parser.add_argument(
        "--as-of-date",
        type=str,
        help="Date for current mileage (YYYY-MM-DD)",
    )
    add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without saving",
    )

    # Edit (vehicle info and/or current mileage)
    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit vehicle info and/or current mileage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml edit --current-miles 58000
  %(prog)s vehicles/brz.yaml edit --current-miles 58000 --as-of-date 2025-01-15
  %(prog)s vehicles/brz.yaml edit --make Subaru --model Impreza --trim "WRX Limited" --dry-run
""",
    )
    edit_parser.add_argument("--make", type=str, help="Make")
    edit_parser.add_argument("--model", type=str, help="Model")
    edit_parser.add_argument("--trim", type=str, help="Trim")
    edit_parser.add_argument("--year", type=int, help="Year")
    edit_parser.add_argument("--purchase-date", type=str, help="Purchase date (YYYY-MM-DD)")
    edit_parser.add_argument("--purchase-miles", type=float, help="Mileage at purchase")
    edit_parser.add_argument(
        "--current-miles",
        type=float,
        help="Current mileage",
    )
    edit_parser.add_argument(
        "--as-of-date",
        type=str,
        help="Date for current mileage (YYYY-MM-DD)",
    )
    edit_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving",
    )

    # Delete (vehicle file)
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete the vehicle file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml delete --force
  %(prog)s vehicles/brz.yaml delete --dry-run
""",
    )
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Confirm deletion (required)",
    )
    delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without saving",
    )

    # Rules subcommand (with nested edit/delete)
    rules_parser = subparsers.add_parser(
        "rules",
        help="List or modify maintenance rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml rules
  %(prog)s vehicles/brz.yaml rules --show-index
""",
    )
    rules_parser.add_argument(
        "--show-index",
        action="store_true",
        help="Show index column for use with: maint rules edit/delete <index> ...",
    )
    rules_sub = rules_parser.add_subparsers(dest="rules_command", required=False)
    rules_add_parser = rules_sub.add_parser(
        "add",
        help="Add a new rule",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml rules add --item "cabin air filter" --verb replace --interval-miles 15000
  %(prog)s vehicles/brz.yaml rules add --item "engine oil and filter" --verb replace --interval-miles 7500 --dry-run
""",
    )
    rules_add_parser.add_argument("--item", type=str, required=True, help="Item name (e.g., engine oil and filter)")
    rules_add_parser.add_argument("--verb", type=str, required=True, help="Verb (e.g., replace, inspect)")
    rules_add_parser.add_argument("--phase", type=str, help="Phase (e.g., initial, ongoing)")
    rules_add_parser.add_argument(
        "--interval-miles",
        type=float,
        help="Normal interval in miles",
    )
    rules_add_parser.add_argument(
        "--interval-months",
        type=float,
        help="Normal interval in months",
    )
    rules_add_parser.add_argument(
        "--severe-interval-miles",
        type=float,
        help="Severe interval in miles",
    )
    rules_add_parser.add_argument(
        "--severe-interval-months",
        type=float,
        help="Severe interval in months",
    )
    rules_add_parser.add_argument("--notes", type=str, help="Notes")
    rules_add_parser.add_argument(
        "--start-miles",
        type=float,
        help="Rule active from this mileage",
    )
    rules_add_parser.add_argument(
        "--stop-miles",
        type=float,
        help="Rule active until this mileage",
    )
    rules_add_parser.add_argument(
        "--start-months",
        type=float,
        help="Rule active from this month",
    )
    rules_add_parser.add_argument(
        "--stop-months",
        type=float,
        help="Rule active until this month",
    )
    rules_add_parser.add_argument(
        "--set-aftermarket",
        type=str,
        metavar="true|false",
        help="Set aftermarket flag (true/false)",
    )
    rules_add_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be added without saving",
    )
    rules_edit_parser = rules_sub.add_parser(
        "edit",
        help="Edit a rule by index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml rules edit 0 --interval-miles 7500
  %(prog)s vehicles/brz.yaml rules edit 0 --interval-miles 5000 --dry-run
""",
    )
    rules_edit_parser.add_argument(
        "index",
        type=int,
        help="Rule index (from: maint rules --show-index)",
    )
    rules_edit_parser.add_argument("--item", type=str, help="Item name (e.g., engine oil and filter)")
    rules_edit_parser.add_argument("--verb", type=str, help="Verb (e.g., replace, inspect)")
    rules_edit_parser.add_argument("--phase", type=str, help="Phase (e.g., initial, ongoing)")
    rules_edit_parser.add_argument(
        "--interval-miles",
        type=float,
        help="Normal interval in miles",
    )
    rules_edit_parser.add_argument(
        "--interval-months",
        type=float,
        help="Normal interval in months",
    )
    rules_edit_parser.add_argument(
        "--severe-interval-miles",
        type=float,
        help="Severe interval in miles",
    )
    rules_edit_parser.add_argument(
        "--severe-interval-months",
        type=float,
        help="Severe interval in months",
    )
    rules_edit_parser.add_argument("--notes", type=str, help="Notes")
    rules_edit_parser.add_argument(
        "--start-miles",
        type=float,
        help="Rule active from this mileage",
    )
    rules_edit_parser.add_argument(
        "--stop-miles",
        type=float,
        help="Rule active until this mileage",
    )
    rules_edit_parser.add_argument(
        "--start-months",
        type=float,
        help="Rule active from this month",
    )
    rules_edit_parser.add_argument(
        "--stop-months",
        type=float,
        help="Rule active until this month",
    )
    rules_edit_parser.add_argument(
        "--set-aftermarket",
        type=str,
        metavar="true|false",
        help="Set aftermarket flag (true/false)",
    )
    rules_edit_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without saving",
    )
    rules_delete_parser = rules_sub.add_parser(
        "delete",
        help="Delete a rule by index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/brz.yaml rules delete 0
  %(prog)s vehicles/brz.yaml rules delete 0 --dry-run
""",
    )
    rules_delete_parser.add_argument(
        "index",
        type=int,
        help="Rule index (from: maint rules --show-index)",
    )
    rules_delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without saving",
    )

    args = parser.parse_args()

    # Validate vehicle file: for "add" it must not exist; otherwise it must exist
    if args.command == "add":
        if args.vehicle_file.exists():
            print(f"Error: File already exists: {args.vehicle_file}")
            return 1
    else:
        if not args.vehicle_file.exists():
            print(f"Error: File not found: {args.vehicle_file}")
            return 1

    # Dispatch to command handler
    if args.command == "status":
        return cmd_status(args)
    elif args.command == "history":
        if getattr(args, "history_command", None) == "add":
            return cmd_log(args)
        if getattr(args, "history_command", None) == "edit":
            return cmd_edit(args)
        if getattr(args, "history_command", None) == "delete":
            return cmd_delete(args)
        return cmd_history(args)
    elif args.command == "add":
        return cmd_vehicle_create(args)
    elif args.command == "edit":
        return cmd_vehicle_edit(args)
    elif args.command == "delete":
        return cmd_vehicle_delete(args)
    elif args.command == "rules":
        if getattr(args, "rules_command", None) == "add":
            return cmd_rules_add(args)
        if getattr(args, "rules_command", None) == "edit":
            return cmd_edit_rule(args)
        if getattr(args, "rules_command", None) == "delete":
            return cmd_delete_rule(args)
        return cmd_rules(args)

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
