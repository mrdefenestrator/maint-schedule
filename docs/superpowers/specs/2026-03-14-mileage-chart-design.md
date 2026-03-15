# Mileage Over Time Chart

Visualize vehicle mileage progression over time with service annotations, available as both a CLI command (ASCII terminal chart) and a web UI feature (Chart.js interactive chart).

## CLI Command

### Usage

```bash
uv run python maint.py vehicles/wrx.yaml chart
uv run python maint.py vehicles/wrx.yaml chart --rule oil
```

### Behavior

- New `chart` subcommand in `maint.py` argparse, following the same pattern as `status`/`history`/`rules`
- Uses `plotext` library for ASCII terminal charts
- Plots mileage (y-axis) vs. date (x-axis) as a line chart
- Service markers shown as dots on the mileage line
- Markers are grouped when multiple services share the same date/mileage pair:
  - Single-service points get one marker style
  - Multi-service points get a distinct marker style
- Supports `--rule <text>` flag to filter which service markers are shown (case-insensitive substring match, same as existing `history --rule`). The mileage line is always drawn in full regardless of filter.

### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `vehicle_file` | positional | Path to vehicle YAML file (inherited from parent parser) |
| `--rule` | optional str | Filter service markers to rules containing this text |

### Data Extraction

- Load vehicle via `load_vehicle(path)`
- Filter `vehicle.history` to entries where `mileage is not None`
- Sort by date ascending
- Group entries sharing the same `(date, mileage)` pair
- Plot date vs. mileage as a line, overlay grouped markers

### Dependency

- Add `plotext` to `pyproject.toml` dependencies

## Web App — History Tab Sparkline

### Location

Top of the History tab (`history.html`), above the year-grouped service entries.

### Appearance

- Compact clickable card (~80px height)
- Contains a sparkline showing mileage trend over time (line only, no axes or markers)
- Left label: start year (e.g., "2012")
- Right label: current mileage (e.g., "104,980 mi")
- "View full chart →" link text in the card header
- Clicking anywhere on the card navigates to `/vehicle/<vehicle_id>/chart`

### Implementation

- New partial template: `web/templates/partials/mileage_sparkline.html`
- Rendered with Chart.js in a minimal configuration (no axes, no tooltips, no legend)
- Chart.js and adapter scripts loaded only when this partial is present
- Data passed from Flask route as JSON via Jinja2 `tojson` filter

### Route Changes

- The existing `/vehicle/<vehicle_id>/history` route needs to pass sparkline data (list of `{date, mileage}` objects) to the template context

## Web App — Full Chart Page

### Route

`GET /vehicle/<vehicle_id>/chart`

### Template

`web/templates/chart.html` extending `vehicle_base.html` to get the vehicle header and tab navigation. The chart page is not a tab itself — it is accessed via the sparkline link on the History tab.

### Layout (Option A: Filters Above)

1. **Filter bar** at the top: text input for rule filtering (mirrors CLI `--rule` behavior)
2. **Chart area** below: Chart.js line chart filling available width
3. **Legend** below chart: green dot = single service, amber dot = multiple services

### Chart Configuration

- **Type**: Line chart with scatter overlay for service markers
- **X-axis**: Time scale using `chartjs-adapter-date-fns`
- **Y-axis**: Mileage (formatted with comma separators)
- **Line**: Blue (#3b82f6), mileage progression over time
- **Markers**: Green (#22c55e) for single-service points, amber (#f59e0b) for grouped points
- **Tooltips**: On hover, show date, mileage, and list of services performed at that point
- **Dark mode**: Chart.js theme colors match Tailwind dark mode (detected via existing theme toggle)
- **Responsive**: Chart.js `responsive: true` with `maintainAspectRatio: false`, container has a fixed min-height

### Filtering

- Text input above the chart filters which service markers are displayed
- Filtering is client-side JavaScript (filter the marker dataset, redraw)
- The mileage line is always shown in full regardless of filter
- Filter matches rule keys by case-insensitive substring (consistent with CLI and history page)

### CDN Dependencies

Loaded only on `chart.html` and `history.html` (when sparkline is present), not globally:
- `chart.js` (~60KB gzipped)
- `chartjs-adapter-date-fns` (date adapter)
- `date-fns` (required by adapter)

### Data Flow

1. Flask route loads vehicle, extracts history entries with mileage
2. Sorts by date, groups by `(date, mileage)` pair
3. Passes two datasets to template as JSON:
   - `mileage_points`: `[{x: "2012-04-30", y: 2970}, ...]` for the line
   - `service_markers`: `[{x: "2012-04-30", y: 2970, services: ["oil/replace", "tires/rotate"], count: 2}, ...]` for the scatter overlay
4. Template renders Chart.js with these datasets
5. Client-side JS handles filtering and tooltip rendering

## Files Changed/Created

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Edit | Add `plotext` dependency |
| `maint.py` | Edit | Add `chart` subcommand and `cmd_chart` function |
| `web/app.py` | Edit | Add `/vehicle/<id>/chart` route, add sparkline data to history route |
| `web/templates/chart.html` | Create | Full chart page extending `vehicle_base.html` |
| `web/templates/partials/mileage_sparkline.html` | Create | Sparkline card partial for History tab |
| `web/templates/history.html` | Edit | Include sparkline partial at top |
| `tests/test_maint.py` | Edit | Add tests for `chart` subcommand |

## No New Models

All data comes from existing `Vehicle.history` entries. No new model classes, loader functions, or YAML schema changes are needed. The grouping logic (combining entries by date+mileage) is presentation-layer only, implemented in both `cmd_chart` (CLI) and the Flask route (web).
