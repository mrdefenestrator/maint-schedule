# Vehicle Maintenance Schedule

A Python tool for managing and tracking vehicle maintenance schedules using YAML-based rule definitions.

## Overview

This project allows you to define comprehensive maintenance schedules for vehicles and track services performed, including support for:

- **Mileage-based intervals** - Schedule maintenance by miles driven
- **Time-based intervals** - Schedule maintenance by months elapsed
- **Severe driving conditions** - Shorter intervals for demanding use cases
- **Lifecycle rules** - Define when maintenance items start/stop applying (e.g., coolant replacement intervals that change after the first service)
- **Aftermarket parts** - Track maintenance for non-OEM components with their own schedules
- **Maintenance history** - Log services performed with date, mileage, cost, and who performed the work
- **Auto-computed state** - Current mileage is automatically derived from service history

## Project Structure

```
├── models/                # Data models package
│   ├── __init__.py        # Package exports
│   ├── status.py          # Status enum (urgency levels)
│   ├── car.py             # Car class (vehicle identification)
│   ├── rule.py            # Rule class (maintenance intervals)
│   ├── history_entry.py   # HistoryEntry class (service records)
│   ├── service_due.py     # ServiceDue dataclass (calculated status)
│   ├── vehicle.py         # Vehicle class (main aggregate)
│   ├── calculations.py    # Helper functions for due calculations
│   └── loader.py          # YAML loading utilities
├── tests/                 # Test files (1:1 with models)
│   ├── test_status.py
│   ├── test_car.py
│   ├── test_rule.py
│   ├── test_history_entry.py
│   ├── test_service_due.py
│   ├── test_vehicle.py
│   └── test_calculations.py
├── vehicles/              # Vehicle YAML files
│   ├── wrx.yaml           # 2012 Subaru WRX
│   └── brz.yaml           # 2015 Subaru BRZ
├── maint.py               # Unified CLI for all commands
├── validate_yaml.py       # Schema validation script
├── schema.yaml            # YAML schema definition
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # Development/CI dependencies
├── setup.sh               # Environment setup script
├── ci.sh                  # CI checks (lint, test, validate)
└── .mise.toml             # mise configuration (Python + uv versions)
```

## Prerequisites

- [mise](https://mise.jdx.dev/) - Runtime version manager

## Setup

```bash
# Install mise if you haven't already
# See https://mise.jdx.dev/getting-started.html

# Run setup script (installs Python via mise, creates venv, installs deps with uv)
./setup.sh
source .venv/bin/activate
```

Or manually:

```bash
# Install tools via mise
mise install

# Create venv and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Usage

The `maint.py` CLI provides four commands: `status`, `history`, `log`, and `rules`.

### View Maintenance Status

```bash
python maint.py <vehicle-file> status [--severe]

# Examples:
python maint.py vehicles/wrx.yaml status           # Normal driving intervals
python maint.py vehicles/wrx.yaml status --severe  # Severe driving intervals
```

The `--severe` flag switches to severe driving intervals (shorter intervals for demanding conditions like frequent short trips, dusty environments, towing, etc.). If a rule doesn't define a severe interval, it falls back to the normal interval.

### View Maintenance History

```bash
python maint.py <vehicle-file> history [options]

# Examples:
python maint.py vehicles/wrx.yaml history                    # All history
python maint.py vehicles/wrx.yaml history --rule "oil"       # Filter by rule
python maint.py vehicles/wrx.yaml history --since 2023-01-01 # Filter by date
python maint.py vehicles/wrx.yaml history --sort miles       # Sort by mileage
python maint.py vehicles/wrx.yaml history --asc              # Ascending order
```

**Options:**
- `--rule <text>` - Filter to rules containing text (case-insensitive)
- `--since <YYYY-MM-DD>` - Show only entries since date
- `--sort <date|miles|rule>` - Sort order (default: date)
- `--asc` - Sort ascending instead of descending

### Log a Service Entry

```bash
python maint.py <vehicle-file> log <rule-key> [options]

# Examples:
python maint.py vehicles/wrx.yaml log "engine oil and filter/replace" --mileage 95000 --by self
python maint.py vehicles/wrx.yaml log "tires/rotate" --mileage 95000 --cost 25.00 --dry-run
```

**Options:**
- `--date <YYYY-MM-DD>` - Service date (default: today)
- `--mileage <number>` - Odometer reading at time of service
- `--by <text>` - Who performed the service (e.g., "self", "Dealer")
- `--notes <text>` - Additional details
- `--cost <number>` - Cost of service
- `--dry-run` - Show what would be added without saving

### List Maintenance Rules

```bash
python maint.py <vehicle-file> rules

# Example:
python maint.py vehicles/brz.yaml rules
```

## Vehicle File Format

Each vehicle has a YAML file (e.g., `wrx-rules.yaml`) containing four sections:

### Vehicle Information

```yaml
car:
  make: Subaru
  model: Impreza
  trim: WRX Limited
  year: 2012
  purchaseDate: '2012-03-23'
  purchaseMiles: 6
```

### Vehicle State

```yaml
state:
  # currentMiles auto-computed from history if not set
  # asOfDate defaults to today if not set
```

The `currentMiles` is automatically computed as the maximum mileage from the history log. You can override it by setting an explicit value.

### Maintenance History

```yaml
history:
  - ruleKey: engine oil and filter/replace
    date: '2025-01-15'
    mileage: 94500
    performedBy: self
    notes: "Motul 5W-30 synthetic"
    cost: 45.00
```

| Property | Required | Description |
|----------|----------|-------------|
| `ruleKey` | Yes | Natural key of the rule (e.g., `engine oil and filter/replace`) |
| `date` | Yes | Date service was performed (ISO 8601) |
| `mileage` | No | Odometer reading at time of service |
| `performedBy` | No | Who did the work (e.g., "self", "Subaru of Springfield") |
| `notes` | No | Additional details about the service |
| `cost` | No | Cost of the service |

### Maintenance Rules

```yaml
rules:
  - item: engine oil and filter
    verb: replace
    intervalMiles: 7500
    intervalMonths: 7.5
    severeIntervalMiles: 3750
    severeIntervalMonths: 3.75
    notes: >
      Under severe driving replace every 3,750 miles.
```

### Rule Properties

| Property | Required | Description |
|----------|----------|-------------|
| `item` | Yes | The component or system |
| `verb` | Yes | Action to perform (inspect, replace, clean, perform) |
| `phase` | No | Lifecycle phase: `initial` or `ongoing` (for rules with different intervals at different vehicle life stages) |
| `intervalMiles` | No* | Normal interval in miles |
| `intervalMonths` | No* | Normal interval in months |
| `severeIntervalMiles` | No | Severe driving interval in miles |
| `severeIntervalMonths` | No | Severe driving interval in months |
| `notes` | No | Additional information or context |
| `startMiles` | No | Mile threshold when this rule becomes active |
| `stopMiles` | No | Mile threshold when this rule stops applying |
| `startMonths` | No | Month threshold when this rule becomes active |
| `stopMonths` | No | Month threshold when this rule stops applying |
| `aftermarket` | No | Boolean flag for non-OEM parts |

*At least one of `intervalMiles` or `intervalMonths` should be provided.

### Rule Keys

Each rule has a natural key constructed from `item/verb/phase`:

- `engine oil and filter/replace` - simple rule (no phase)
- `engine coolant/replace/initial` - first coolant replacement
- `engine coolant/replace/ongoing` - subsequent coolant replacements

These keys are used to uniquely identify rules and link history entries to the corresponding rule.

### Lifecycle Rules Example

Some maintenance items have different intervals at different points in the vehicle's life. Use the `phase` field to distinguish between them:

```yaml
# First coolant replacement (0-137,500 miles)
# Key: engine coolant/replace/initial
- item: engine coolant
  verb: replace
  phase: initial
  intervalMiles: 137500
  intervalMonths: 132
  stopMiles: 137500
  stopMonths: 132

# Subsequent coolant replacements (after 137,500 miles)
# Key: engine coolant/replace/ongoing
- item: engine coolant
  verb: replace
  phase: ongoing
  intervalMiles: 75000
  intervalMonths: 72
  startMiles: 137500
  startMonths: 132
```

## Service Due Calculation

The system calculates when each service is due based on these rules:

### Core Assumptions

1. **Fresh at zero** - All vehicle systems are assumed fresh when the car was built (0 miles on odometer)
2. **Service-based intervals** - After any service, the next due is calculated from when you *actually* did it, not when it was scheduled
3. **Whichever comes first** - Services are due when *either* the mileage OR time threshold is crossed

### Calculation Logic

| Scenario | How "Next Due" is Calculated |
|----------|------------------------------|
| No service history | Due at `startMiles + intervalMiles` (startMiles defaults to 0) |
| Has service history | Due at `lastServiceMiles + intervalMiles` |
| Time-based only (no miles) | Due at `lastServiceDate + intervalMonths` |

For parts added later (aftermarket), set `startMiles` to when the part was installed. The first service will be due at `startMiles + intervalMiles`.

### Lifecycle Rules

When looking up service history, the system matches on **item + verb** regardless of phase. This allows lifecycle phases to hand off correctly:

1. You service coolant at 140,000 mi, log as `engine coolant/replace/initial`
2. At 200,000 mi, the "ongoing" rule is now active (startMiles: 137500)
3. System finds last coolant service at 140,000 mi (ignoring phase)
4. Next due: 140,000 + 75,000 = 215,000 mi

### Start/Stop Thresholds

- `startMiles` / `stopMiles` define when a rule is **active**
- Rules outside the current mileage range are marked **INACTIVE**
- Use case: Parts that were added later (aftermarket) or removed

### Status Categories

| Status | Meaning |
|--------|---------|
| **OVERDUE** | Past due mileage OR past due date |
| **DUE_SOON** | Within 1,000 miles OR 1 month of due |
| **OK** | Not yet due |
| **INACTIVE** | Rule doesn't apply at current mileage |
| **UNKNOWN** | Cannot calculate (e.g., time-only rule with no history) |
