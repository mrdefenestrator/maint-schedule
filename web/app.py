"""Flask web application for vehicle maintenance tracking."""

import os
from datetime import date
from pathlib import Path
from glob import glob

from flask import Flask, make_response, render_template, request, redirect, url_for, flash

# Add parent directory to path for model imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.loader import (
    load_vehicle,
    save_history_entry,
    save_current_miles,
    update_history_entry,
    delete_history_entry,
    add_rule,
    update_rule,
    delete_rule,
)
from models.history_entry import HistoryEntry
from models.rule import Rule
from models.status import Status

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# Path to vehicles directory (relative to project root)
VEHICLES_DIR = Path(__file__).parent.parent / "vehicles"


def get_vehicle_files():
    """Get all vehicle YAML files."""
    return sorted(VEHICLES_DIR.glob("*.yaml"))


def get_vehicle_id(path: Path) -> str:
    """Extract vehicle ID from path (filename without extension)."""
    return path.stem


def get_vehicle_path(vehicle_id: str) -> Path:
    """Get full path for a vehicle ID."""
    return VEHICLES_DIR / f"{vehicle_id}.yaml"


def format_miles(miles):
    """Format miles with comma separator."""
    if miles is None:
        return "—"
    return f"{miles:,.0f}"


def format_date(date_str):
    """Format date for display."""
    if date_str is None:
        return "—"
    return date_str


def format_time_remaining(days):
    """Format time remaining as 'X days' or 'X days over' (delta)."""
    if days is None:
        return "—"
    if days < 0:
        return f"{abs(days):,} days over"
    return f"{days:,} days"


def status_color(status: Status) -> str:
    """Get Tailwind color classes for status."""
    colors = {
        Status.OVERDUE: "bg-red-100 text-red-800 border-red-200",
        Status.DUE_SOON: "bg-yellow-100 text-yellow-800 border-yellow-200",
        Status.OK: "bg-green-100 text-green-800 border-green-200",
        Status.INACTIVE: "bg-gray-100 text-gray-500 border-gray-200",
        Status.UNKNOWN: "bg-purple-100 text-purple-800 border-purple-200",
    }
    return colors.get(status, "bg-gray-100 text-gray-800")


def status_badge_color(status: Status) -> str:
    """Get Tailwind color classes for status badge."""
    colors = {
        Status.OVERDUE: "bg-red-500 text-white",
        Status.DUE_SOON: "bg-yellow-500 text-white",
        Status.OK: "bg-green-500 text-white",
        Status.INACTIVE: "bg-gray-400 text-white",
        Status.UNKNOWN: "bg-purple-500 text-white",
    }
    return colors.get(status, "bg-gray-500 text-white")


def status_display_name(status: Status) -> str:
    """Display label for status (Title Case: Overdue, Due Soon, OK, etc.)."""
    labels = {
        Status.OVERDUE: "Overdue",
        Status.DUE_SOON: "Due Soon",
        Status.OK: "OK",
        Status.INACTIVE: "Inactive",
        Status.UNKNOWN: "Unknown",
    }
    return labels.get(status, status.name.replace("_", " ").title())


def format_rule_key(rule_key):
    """Format rule_key as 'Verb Item [phase]' to match vehicle page display."""
    if not rule_key:
        return "—"
    parts = rule_key.split("/")
    if len(parts) >= 2:
        item = parts[0]
        verb = parts[1]
        phase = parts[2] if len(parts) > 2 else None
        result = f"{verb.title()} {item}"
        if phase:
            result += f" [{phase}]"
        return result
    return rule_key


# Register template filters
app.jinja_env.filters["format_miles"] = format_miles
app.jinja_env.filters["format_date"] = format_date
app.jinja_env.filters["format_time_remaining"] = format_time_remaining
app.jinja_env.filters["format_rule_key"] = format_rule_key
app.jinja_env.filters["status_color"] = status_color
app.jinja_env.filters["status_badge_color"] = status_badge_color
app.jinja_env.filters["status_display_name"] = status_display_name


@app.route("/")
def index():
    """Dashboard showing all vehicles."""
    vehicles = []
    for path in get_vehicle_files():
        vehicle = load_vehicle(path)
        # Get status summary
        all_status = vehicle.get_all_service_status()
        overdue = sum(1 for s in all_status if s.status == Status.OVERDUE)
        due_soon = sum(1 for s in all_status if s.status == Status.DUE_SOON)

        ok = sum(1 for s in all_status if s.status == Status.OK)

        # Get last service info
        last_service = vehicle.last_service

        vehicles.append({
            "id": get_vehicle_id(path),
            "vehicle": vehicle,
            "overdue": overdue,
            "due_soon": due_soon,
            "ok": ok,
            "last_service": last_service,
            "total_rules": len(vehicle.rules),
        })

    return render_template("index.html", vehicles=vehicles)


@app.route("/vehicle/<vehicle_id>")
def vehicle_detail(vehicle_id: str):
    """Vehicle detail page with status table."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    severe = request.args.get("severe", "").lower() == "true"
    status_filter = request.args.get("status", "").lower() or None

    # Get all unique verbs from vehicle rules
    all_verbs = sorted(set(r.verb.lower() for r in vehicle.rules))

    # Show verbs: when "show" params present, only those verbs; when empty, show all
    include_verbs = request.args.getlist("show")
    include_verbs = [v.lower() for v in include_verbs] if include_verbs else None

    all_status = vehicle.get_all_service_status(severe=severe, include_verbs=include_verbs)

    # Calculate counts before filtering for display
    status_counts = {
        'overdue': sum(1 for s in all_status if s.status == Status.OVERDUE),
        'due_soon': sum(1 for s in all_status if s.status == Status.DUE_SOON),
        'ok': sum(1 for s in all_status if s.status == Status.OK),
        'inactive': sum(1 for s in all_status if s.status == Status.INACTIVE),
        'unknown': sum(1 for s in all_status if s.status == Status.UNKNOWN),
    }

    # Filter by status if requested
    filtered_status = all_status
    if status_filter:
        status_map = {
            'overdue': Status.OVERDUE,
            'due_soon': Status.DUE_SOON,
            'ok': Status.OK,
            'inactive': Status.INACTIVE,
            'unknown': Status.UNKNOWN,
        }
        if status_filter in status_map:
            filtered_status = [s for s in all_status if s.status == status_map[status_filter]]

    # Sort by urgency (OVERDUE first, then DUE_SOON, etc.)
    filtered_status.sort(key=lambda s: (s.status.value, s.rule.item))

    return render_template(
        "vehicle.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        all_status=filtered_status,
        status_counts=status_counts,
        severe=severe,
        all_verbs=all_verbs,
        include_verbs=include_verbs or [],
        status_filter=status_filter,
        Status=Status,
        active_tab='status',
        standalone=False,
    )


@app.route("/vehicle/<vehicle_id>/status")
def vehicle_status_partial(vehicle_id: str):
    """HTMX partial: status table for a vehicle."""
    path = get_vehicle_path(vehicle_id)
    vehicle = load_vehicle(path)

    severe = request.args.get("severe", "").lower() == "true"
    exclude_inspect = request.args.get("exclude_inspect", "").lower() == "true"

    exclude_verbs = ["inspect"] if exclude_inspect else None
    all_status = vehicle.get_all_service_status(severe=severe, exclude_verbs=exclude_verbs)
    all_status.sort(key=lambda s: (s.status.value, s.rule.item))

    return render_template(
        "partials/status_table.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        all_status=all_status,
        severe=severe,
        exclude_inspect=exclude_inspect,
        Status=Status,
    )


@app.route("/vehicle/<vehicle_id>/log", methods=["GET"])
def log_service_form(vehicle_id: str):
    """HTMX partial: log service form."""
    path = get_vehicle_path(vehicle_id)
    vehicle = load_vehicle(path)

    # Get active rules for dropdown
    rules = [r for r in vehicle.rules if r.is_active_at(vehicle.current_miles or 0)]
    rules.sort(key=lambda r: r.key)

    return render_template(
        "partials/log_form.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        rules=rules,
        today=date.today().isoformat(),
    )


@app.route("/vehicle/<vehicle_id>/log", methods=["POST"])
def log_service(vehicle_id: str):
    """Handle log service form submission."""
    path = get_vehicle_path(vehicle_id)

    rule_key = request.form.get("rule_key")
    service_date = request.form.get("date") or date.today().isoformat()
    mileage = request.form.get("mileage")
    performed_by = request.form.get("performed_by") or None
    notes = request.form.get("notes") or None
    cost = request.form.get("cost")

    # Validate
    if not rule_key:
        flash("Please select a service", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    # Parse numeric fields
    mileage_val = float(mileage) if mileage else None
    cost_val = float(cost) if cost else None

    # Create and save entry
    entry = HistoryEntry(
        rule_key=rule_key,
        date=service_date,
        mileage=mileage_val,
        performed_by=performed_by,
        notes=notes,
        cost=cost_val,
    )

    save_history_entry(path, entry)
    flash(f"Logged service: {rule_key}", "success")

    # HTMX: redirect to vehicle status so target (#modal-content or #status-table) always works
    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Service logged.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_detail", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/mileage", methods=["GET"])
def update_mileage_form(vehicle_id: str):
    """HTMX partial: update mileage form."""
    path = get_vehicle_path(vehicle_id)
    vehicle = load_vehicle(path)

    return render_template(
        "partials/mileage_form.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
    )


@app.route("/vehicle/<vehicle_id>/mileage", methods=["POST"])
def update_mileage(vehicle_id: str):
    """Handle update mileage form submission."""
    path = get_vehicle_path(vehicle_id)

    mileage = request.form.get("mileage")
    if not mileage:
        flash("Please enter mileage", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    try:
        miles = float(mileage)
    except ValueError:
        flash("Invalid mileage value", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    save_current_miles(path, miles)
    flash(f"Updated mileage to {miles:,.0f}", "success")

    # HTMX: redirect to vehicle status so target (#modal-content or #status-table) always works
    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Mileage updated.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_detail", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/history")
def vehicle_history(vehicle_id: str):
    """Vehicle maintenance history page."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    # (raw_index, entry) sorted by date descending for stable edit indices
    entries_with_index = sorted(
        enumerate(vehicle.history),
        key=lambda ie: ie[1].date,
        reverse=True,
    )

    # Get all unique verbs from history entries (extracted from rule_key: item/verb/phase)
    all_verbs = set()
    for _, entry in entries_with_index:
        parts = entry.rule_key.split("/")
        if len(parts) >= 2:
            all_verbs.add(parts[1].lower())
    all_verbs = sorted(all_verbs)

    # Show verbs: when "show" params present, only those verbs; when empty, show all
    include_verbs = request.args.getlist("show")
    include_verbs = [v.lower() for v in include_verbs] if include_verbs else []

    # Filter history based on include_verbs
    if include_verbs:
        filtered = []
        for idx, entry in entries_with_index:
            parts = entry.rule_key.split("/")
            verb = parts[1].lower() if len(parts) >= 2 else ""
            if verb in include_verbs:
                filtered.append((idx, entry))
        entries_with_index = filtered

    total_cost = sum(e.cost for _, e in entries_with_index if e.cost is not None)

    all_status = vehicle.get_all_service_status(severe=False)
    status_counts = {
        'overdue': sum(1 for s in all_status if s.status == Status.OVERDUE),
        'due_soon': sum(1 for s in all_status if s.status == Status.DUE_SOON),
        'ok': sum(1 for s in all_status if s.status == Status.OK),
    }

    return render_template(
        "history.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        history_with_index=entries_with_index,
        total_cost=total_cost,
        all_verbs=all_verbs,
        include_verbs=include_verbs,
        status_counts=status_counts,
        active_tab='history',
    )


@app.route("/vehicle/<vehicle_id>/history/<int:index>/edit", methods=["GET"])
def edit_history_form(vehicle_id: str, index: int):
    """HTMX partial: edit history entry form."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        return "Vehicle not found", 404

    vehicle = load_vehicle(path)
    if index < 0 or index >= len(vehicle.history):
        return "History entry not found", 404

    entry = vehicle.history[index]
    rules = sorted(vehicle.rules, key=lambda r: r.key)

    return render_template(
        "partials/edit_history_form.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        entry=entry,
        index=index,
        rules=rules,
    )


@app.route("/vehicle/<vehicle_id>/history/<int:index>/edit", methods=["POST"])
def edit_history(vehicle_id: str, index: int):
    """Handle edit history form submission."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    if index < 0 or index >= len(vehicle.history):
        flash("History entry not found", "error")
        return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))

    rule_key = request.form.get("rule_key")
    service_date = request.form.get("date")
    mileage = request.form.get("mileage")
    performed_by = request.form.get("performed_by") or None
    notes = request.form.get("notes") or None
    cost = request.form.get("cost")

    if not rule_key:
        flash("Please select a service", "error")
        return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))

    mileage_val = float(mileage) if mileage else None
    cost_val = float(cost) if cost else None

    entry = HistoryEntry(
        rule_key=rule_key,
        date=service_date,
        mileage=mileage_val,
        performed_by=performed_by,
        notes=notes,
        cost=cost_val,
    )

    try:
        update_history_entry(path, index, entry)
    except IndexError:
        flash("History entry not found", "error")
        return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))

    flash("History entry updated.", "success")

    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Entry updated.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_history", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/history/<int:index>/delete", methods=["GET", "POST"])
def delete_history(vehicle_id: str, index: int):
    """GET: show delete confirmation modal. POST: delete the history entry."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    if index < 0 or index >= len(vehicle.history):
        flash("History entry not found", "error")
        return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))

    if request.method == "GET":
        entry = vehicle.history[index]
        return render_template(
            "partials/delete_history_confirm.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
            entry=entry,
            index=index,
        )

    try:
        delete_history_entry(path, index)
    except IndexError:
        flash("History entry not found", "error")
        return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))

    flash("History entry deleted.", "success")

    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Entry deleted.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_history", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_history", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/rules/add", methods=["GET", "POST"])
def add_rule_view(vehicle_id: str):
    """GET: show add rule form. POST: create the rule."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)

    if request.method == "GET":
        return render_template(
            "partials/add_rule_form.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
        )

    # POST: parse form and add rule
    item = request.form.get("item", "").strip()
    verb = request.form.get("verb", "").strip()
    phase = request.form.get("phase", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    def _float_or_none(s):
        if s is None or (isinstance(s, str) and not s.strip()):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    interval_miles = _float_or_none(request.form.get("interval_miles"))
    interval_months = _float_or_none(request.form.get("interval_months"))
    severe_interval_miles = _float_or_none(request.form.get("severe_interval_miles"))
    severe_interval_months = _float_or_none(request.form.get("severe_interval_months"))
    start_miles = _float_or_none(request.form.get("start_miles"))
    stop_miles = _float_or_none(request.form.get("stop_miles"))
    start_months = _float_or_none(request.form.get("start_months"))
    stop_months = _float_or_none(request.form.get("stop_months"))
    aftermarket = request.form.get("aftermarket") == "true"

    if not item or not verb:
        flash("Item and verb are required", "error")
        return redirect(url_for("add_rule_view", vehicle_id=vehicle_id))

    rule = Rule(
        item=item,
        verb=verb,
        phase=phase,
        interval_miles=interval_miles,
        interval_months=interval_months,
        severe_interval_miles=severe_interval_miles,
        severe_interval_months=severe_interval_months,
        notes=notes,
        start_miles=start_miles if start_miles is not None else 0,
        stop_miles=stop_miles if stop_miles is not None else 999999999,
        start_months=start_months if start_months is not None else 0,
        stop_months=stop_months if stop_months is not None else 9999,
        aftermarket=aftermarket,
    )

    try:
        add_rule(path, rule)
    except Exception:
        flash("Failed to add rule", "error")
        return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))

    flash("Rule added.", "success")

    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Rule added.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_rules", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/rules/<int:index>/edit", methods=["GET", "POST"])
def edit_rule(vehicle_id: str, index: int):
    """GET: show edit rule form. POST: update the rule."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    if index < 0 or index >= len(vehicle.rules):
        flash("Rule not found", "error")
        return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))

    rule = vehicle.rules[index]

    if request.method == "GET":
        return render_template(
            "partials/edit_rule_form.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
            rule=rule,
            index=index,
        )

    # POST: parse form and update
    item = request.form.get("item", "").strip()
    verb = request.form.get("verb", "").strip()
    phase = request.form.get("phase", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    def _float_or_none(s):
        if s is None or (isinstance(s, str) and not s.strip()):
            return None
        try:
            return float(s)
        except ValueError:
            return None

    interval_miles = _float_or_none(request.form.get("interval_miles"))
    interval_months = _float_or_none(request.form.get("interval_months"))
    severe_interval_miles = _float_or_none(request.form.get("severe_interval_miles"))
    severe_interval_months = _float_or_none(request.form.get("severe_interval_months"))
    start_miles = _float_or_none(request.form.get("start_miles"))
    stop_miles = _float_or_none(request.form.get("stop_miles"))
    start_months = _float_or_none(request.form.get("start_months"))
    stop_months = _float_or_none(request.form.get("stop_months"))
    aftermarket = request.form.get("aftermarket") == "true"

    if not item or not verb:
        flash("Item and verb are required", "error")
        return redirect(url_for("edit_rule", vehicle_id=vehicle_id, index=index))

    updated = Rule(
        item=item,
        verb=verb,
        phase=phase,
        interval_miles=interval_miles,
        interval_months=interval_months,
        severe_interval_miles=severe_interval_miles,
        severe_interval_months=severe_interval_months,
        notes=notes,
        start_miles=start_miles if start_miles is not None else 0,
        stop_miles=stop_miles if stop_miles is not None else 999999999,
        start_months=start_months if start_months is not None else 0,
        stop_months=stop_months if stop_months is not None else 9999,
        aftermarket=aftermarket,
    )

    try:
        update_rule(path, index, updated)
    except IndexError:
        flash("Rule not found", "error")
        return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))

    flash("Rule updated.", "success")

    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Rule updated.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_rules", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/rules/<int:index>/delete", methods=["GET", "POST"])
def delete_rule_view(vehicle_id: str, index: int):
    """GET: show delete confirmation modal. POST: delete the rule."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    if index < 0 or index >= len(vehicle.rules):
        flash("Rule not found", "error")
        return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))

    if request.method == "GET":
        rule = vehicle.rules[index]
        return render_template(
            "partials/delete_rule_confirm.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
            rule=rule,
            index=index,
        )

    try:
        delete_rule(path, index)
    except IndexError:
        flash("Rule not found", "error")
        return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))

    flash("Rule deleted.", "success")

    if request.headers.get("HX-Request"):
        response = make_response(
            render_template("partials/success_redirect.html", message="Rule deleted.")
        )
        response.headers["HX-Redirect"] = url_for("vehicle_rules", vehicle_id=vehicle_id)
        return response

    return redirect(url_for("vehicle_rules", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/rules")
def vehicle_rules(vehicle_id: str):
    """Vehicle maintenance rules/schedule page."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    current_miles = vehicle.current_miles or 0
    status_filter = request.args.get("status", "").lower() or None

    # Get all unique verbs from rules
    all_verbs = sorted(set(r.verb.lower() for r in vehicle.rules))

    # Show verbs: when "show" params present, only those verbs; when empty, show all
    include_verbs = request.args.getlist("show")
    include_verbs = [v.lower() for v in include_verbs] if include_verbs else []

    # Build (raw_index, rule) and filter
    rules_with_index = list(enumerate(vehicle.rules))
    if include_verbs:
        rules_with_index = [
            (i, r) for i, r in rules_with_index
            if r.verb.lower() in include_verbs
        ]

    # Count active vs inactive (before status filter, after verb filter)
    active_count = sum(1 for _, r in rules_with_index if r.is_active_at(current_miles))
    inactive_count = len(rules_with_index) - active_count

    # Filter by status if requested
    if status_filter == "active":
        rules_with_index = [(i, r) for i, r in rules_with_index if r.is_active_at(current_miles)]
    elif status_filter == "inactive":
        rules_with_index = [(i, r) for i, r in rules_with_index if not r.is_active_at(current_miles)]

    # Group by item: rules_by_item[item] = [(index, rule), ...]
    rules_by_item = {}
    for index, rule in rules_with_index:
        if rule.item not in rules_by_item:
            rules_by_item[rule.item] = []
        rules_by_item[rule.item].append((index, rule))

    # Sort items alphabetically, and rules within each item by verb
    sorted_items = sorted(rules_by_item.keys())
    for item in sorted_items:
        rules_by_item[item].sort(key=lambda ir: (ir[1].verb, ir[1].phase or ""))

    all_status = vehicle.get_all_service_status(severe=False)
    status_counts = {
        'overdue': sum(1 for s in all_status if s.status == Status.OVERDUE),
        'due_soon': sum(1 for s in all_status if s.status == Status.DUE_SOON),
        'ok': sum(1 for s in all_status if s.status == Status.OK),
    }

    return render_template(
        "rules.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        rules_by_item=rules_by_item,
        sorted_items=sorted_items,
        current_miles=current_miles,
        active_count=active_count,
        inactive_count=inactive_count,
        status_filter=status_filter,
        all_verbs=all_verbs,
        include_verbs=include_verbs,
        status_counts=status_counts,
        active_tab='rules',
    )


if __name__ == "__main__":
    # Run with debug mode for development
    # Access from phone: use your computer's local IP (e.g., 192.168.1.x:5001)
    # Using 5001 to avoid conflict with macOS AirPlay Receiver on 5000
    app.run(debug=True, host="0.0.0.0", port=5001)
