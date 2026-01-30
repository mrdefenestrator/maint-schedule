"""Flask web application for vehicle maintenance tracking."""

import os
from datetime import date
from pathlib import Path
from glob import glob

from flask import Flask, render_template, request, redirect, url_for, flash

# Add parent directory to path for model imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.loader import load_vehicle, save_history_entry, save_current_miles
from models.history_entry import HistoryEntry
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


def format_rule_key(rule_key):
    """Format rule_key as 'Verb Item [phase]' to match vehicle page display."""
    if not rule_key:
        return "—"
    parts = rule_key.split("/")
    if len(parts) >= 2:
        item = parts[0]
        verb = parts[1]
        phase = parts[2] if len(parts) > 2 else None
        result = f"{verb.capitalize()} {item}"
        if phase:
            result += f" [{phase}]"
        return result
    return rule_key


# Register template filters
app.jinja_env.filters["format_miles"] = format_miles
app.jinja_env.filters["format_date"] = format_date
app.jinja_env.filters["format_rule_key"] = format_rule_key
app.jinja_env.filters["status_color"] = status_color
app.jinja_env.filters["status_badge_color"] = status_badge_color


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

    # Get excluded verbs from query string (can be multiple)
    exclude_verbs = request.args.getlist("exclude")
    exclude_verbs = [v.lower() for v in exclude_verbs] if exclude_verbs else None

    all_status = vehicle.get_all_service_status(severe=severe, exclude_verbs=exclude_verbs)

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
        exclude_verbs=exclude_verbs or [],
        status_filter=status_filter,
        Status=Status,
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

    # Return updated status table for HTMX
    if request.headers.get("HX-Request"):
        vehicle = load_vehicle(path)
        all_status = vehicle.get_all_service_status()
        all_status.sort(key=lambda s: (s.status.value, s.rule.item))
        return render_template(
            "partials/status_table.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
            all_status=all_status,
            severe=False,
            exclude_inspect=False,
            Status=Status,
        )

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

    # Return updated status table for HTMX
    if request.headers.get("HX-Request"):
        vehicle = load_vehicle(path)
        all_status = vehicle.get_all_service_status()
        all_status.sort(key=lambda s: (s.status.value, s.rule.item))
        return render_template(
            "partials/status_table.html",
            vehicle_id=vehicle_id,
            vehicle=vehicle,
            all_status=all_status,
            severe=False,
            exclude_inspect=False,
            Status=Status,
        )

    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/vehicle/<vehicle_id>/history")
def vehicle_history(vehicle_id: str):
    """Vehicle maintenance history page."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    history = vehicle.get_history_sorted(sort_by="date", reverse=True)

    return render_template(
        "history.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        history=history,
    )


if __name__ == "__main__":
    # Run with debug mode for development
    # Access from phone: use your computer's local IP (e.g., 192.168.1.x:5001)
    # Using 5001 to avoid conflict with macOS AirPlay Receiver on 5000
    app.run(debug=True, host="0.0.0.0", port=5001)
