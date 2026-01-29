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
├── schedule.py        # Main Python script with Vehicle, Rule, and HistoryEntry classes
├── schema.yaml        # YAML schema definition for validation
├── wrx-rules.yaml     # Vehicle file for a 2012 Subaru WRX (rules + history)
├── brz-rules.yaml     # Vehicle file for a 2015 Subaru BRZ (rules + history)
├── requirements.txt   # Python dependencies
├── setup.sh           # Environment setup script
└── .mise.toml         # mise configuration (Python + uv versions)
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

```bash
python schedule.py
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

## Requirements

- Python 3.12+ (managed via mise)
- PyYAML 6.0+
- [uv](https://github.com/astral-sh/uv) (installed via mise)
