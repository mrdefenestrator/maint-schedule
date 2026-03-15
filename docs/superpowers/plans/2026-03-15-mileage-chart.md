# Mileage Chart Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a mileage-over-time chart with service annotations to both the CLI (ASCII via plotext) and the web UI (Chart.js interactive chart).

**Architecture:** A new `extract_chart_data()` helper in `maint.py` handles data extraction/grouping for the CLI. Two helper functions in `web/app.py` (`_build_mileage_points`, `_build_service_markers`) prepare JSON-serializable data for Chart.js. The history tab gets a compact sparkline linking to a dedicated full chart page at `/vehicle/<id>/chart`.

**Tech Stack:** plotext (CLI ASCII charts), Chart.js 4 + chartjs-adapter-date-fns 3 + date-fns 3 (web, loaded from CDN)

**Spec:** `docs/superpowers/specs/2026-03-14-mileage-chart-design.md`

---

## Chunk 1: CLI Chart Command

### Task 1: Add plotext dependency

**Files:**
- Modify: `pyproject.toml:5-9`

- [ ] **Step 1: Add plotext to dependencies**

In `pyproject.toml`, add `"plotext>=5.2"` to the `dependencies` list:

```toml
dependencies = [
    "PyYAML>=6.0",
    "python-dateutil>=2.8",
    "tabulate>=0.9",
    "flask>=3.0",
    "plotext>=5.2",
]
```

- [ ] **Step 2: Install**

Run: `uv sync`
Expected: plotext installed into `.venv/`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "add plotext dependency for CLI charts"
```

---

### Task 2: Chart data extraction — tests and implementation

**Files:**
- Modify: `maint.py` (add `extract_chart_data` function)
- Modify: `tests/test_maint.py` (add `TestExtractChartData` class)

The `extract_chart_data(vehicle, rule_filter=None)` function extracts mileage timeline data and grouped service markers from a Vehicle object. It is a pure function (no I/O, no plotext calls) so it's easy to test.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_maint.py`. First, update the imports at the top of the file:

```python
from maint import (
    format_miles,
    format_cost,
    format_remaining,
    format_time_remaining,
    truncate,
    make_status_table,
    make_history_table,
    extract_chart_data,
)
```

Then add at the end of the file:

```python
class TestExtractChartData:
    """Tests for extract_chart_data."""

    def _make_vehicle(self, history=None):
        car = Car(
            make="Test",
            model="Car",
            trim=None,
            year=2020,
            purchase_date="2020-01-01",
            purchase_miles=100,
        )
        return Vehicle(car=car, rules=[], history=history or [])

    def test_no_history_returns_none(self):
        vehicle = self._make_vehicle()
        assert extract_chart_data(vehicle) is None

    def test_single_entry_returns_none(self):
        """Purchase point + 0 history entries with mileage = 1 point total."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=None
                )
            ]
        )
        assert extract_chart_data(vehicle) is None

    def test_basic_extraction(self):
        """Purchase + 2 entries = 3 line points, 2 single markers."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=5000
                ),
                HistoryEntry(
                    rule_key="oil/replace", date="2021-01-01", mileage=10000
                ),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        assert result["line_dates"] == ["2020-01-01", "2020-06-01", "2021-01-01"]
        assert result["line_mileages"] == [100, 5000, 10000]
        assert len(result["single_dates"]) == 2
        assert len(result["multi_dates"]) == 0

    def test_grouped_markers(self):
        """Two services on same date/mileage create a multi marker."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=5000
                ),
                HistoryEntry(
                    rule_key="tires/rotate", date="2020-06-01", mileage=5000
                ),
                HistoryEntry(
                    rule_key="oil/replace", date="2021-01-01", mileage=10000
                ),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        # Line has 3 unique points: purchase + 2 unique (date, mileage)
        assert len(result["line_dates"]) == 3
        # 5000mi has 2 services -> multi, 10000mi has 1 -> single
        assert result["single_dates"] == ["2021-01-01"]
        assert result["single_mileages"] == [10000]
        assert result["multi_dates"] == ["2020-06-01"]
        assert result["multi_mileages"] == [5000]

    def test_rule_filter(self):
        """--rule filter only affects markers, not line data."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=5000
                ),
                HistoryEntry(
                    rule_key="tires/rotate", date="2020-06-01", mileage=5000
                ),
                HistoryEntry(
                    rule_key="oil/replace", date="2021-01-01", mileage=10000
                ),
            ]
        )
        result = extract_chart_data(vehicle, rule_filter="oil")
        assert result is not None
        # Line still has all 3 points
        assert len(result["line_dates"]) == 3
        # Only oil entries match: 5000mi has 1 oil -> single, 10000mi has 1 oil -> single
        assert len(result["single_dates"]) == 2
        assert len(result["multi_dates"]) == 0

    def test_entries_without_mileage_excluded(self):
        """History entries with mileage=None are excluded from everything."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=None
                ),
                HistoryEntry(
                    rule_key="oil/replace", date="2021-01-01", mileage=10000
                ),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result is not None
        # Purchase + 1 entry with mileage = 2 points
        assert len(result["line_dates"]) == 2
        assert result["line_dates"] == ["2020-01-01", "2021-01-01"]

    def test_sorted_by_date(self):
        """Output is sorted by date regardless of input order."""
        vehicle = self._make_vehicle(
            history=[
                HistoryEntry(
                    rule_key="oil/replace", date="2021-01-01", mileage=10000
                ),
                HistoryEntry(
                    rule_key="oil/replace", date="2020-06-01", mileage=5000
                ),
            ]
        )
        result = extract_chart_data(vehicle)
        assert result["line_dates"] == ["2020-01-01", "2020-06-01", "2021-01-01"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_maint.py::TestExtractChartData -v`
Expected: FAIL — `ImportError: cannot import name 'extract_chart_data'`

- [ ] **Step 3: Implement extract_chart_data**

Add to `maint.py`, after the existing formatting helpers (after the `truncate` function, around line 93) and before the status command section:

Add `from collections import defaultdict` to the imports at the top of `maint.py` (after line 6, `from pathlib import Path`).

Then add the function after the `truncate` function, before the status command section:

```python
def extract_chart_data(vehicle, rule_filter=None):
    """Extract mileage timeline and grouped service markers for charting.

    Returns None if fewer than 2 data points are available.
    Otherwise returns a dict with:
    - line_dates: list of date strings for the mileage line
    - line_mileages: list of mileage floats for the mileage line
    - single_dates/single_mileages: points where 1 service occurred
    - multi_dates/multi_mileages: points where 2+ services occurred
    """
    # Collect unique (date, mileage) points for the line
    points = {(vehicle.car.purchase_date, vehicle.car.purchase_miles)}
    for entry in vehicle.history:
        if entry.mileage is not None:
            points.add((entry.date, entry.mileage))

    if len(points) < 2:
        return None

    sorted_points = sorted(points, key=lambda p: p[0])
    line_dates = [p[0] for p in sorted_points]
    line_mileages = [p[1] for p in sorted_points]

    # Group services by (date, mileage) for markers
    groups = defaultdict(list)
    for entry in vehicle.history:
        if entry.mileage is not None:
            if rule_filter is None or rule_filter.lower() in entry.rule_key.lower():
                groups[(entry.date, entry.mileage)].append(entry.rule_key)

    single_dates, single_mileages = [], []
    multi_dates, multi_mileages = [], []
    for (date, miles), services in sorted(groups.items()):
        if len(services) == 1:
            single_dates.append(date)
            single_mileages.append(miles)
        else:
            multi_dates.append(date)
            multi_mileages.append(miles)

    return {
        "line_dates": line_dates,
        "line_mileages": line_mileages,
        "single_dates": single_dates,
        "single_mileages": single_mileages,
        "multi_dates": multi_dates,
        "multi_mileages": multi_mileages,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_maint.py::TestExtractChartData -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add maint.py tests/test_maint.py
git commit -m "add extract_chart_data helper with tests"
```

---

### Task 3: Chart command function and argparse wiring

**Files:**
- Modify: `maint.py` (add `cmd_chart`, add `chart` subparser, add dispatch)

- [ ] **Step 1: Add cmd_chart function**

Add to `maint.py`, after the `cmd_rules` function (around line 876) and before the `main()` function:

```python
# =============================================================================
# Chart command
# =============================================================================


def cmd_chart(args):
    """Show mileage over time with service markers."""
    import plotext as plt

    vehicle = load_vehicle(args.vehicle_file)
    data = extract_chart_data(vehicle, rule_filter=args.rule)

    if data is None:
        has_mileage_entries = any(
            e.mileage is not None for e in vehicle.history
        )
        if has_mileage_entries:
            print(
                "Not enough mileage data to chart (need at least 2 data points)."
            )
        else:
            print("No mileage data to chart.")
        return 0

    plt.date_form("Y-m-d")
    plt.plot(data["line_dates"], data["line_mileages"], label="Mileage")

    if data["single_dates"]:
        plt.scatter(
            data["single_dates"],
            data["single_mileages"],
            marker="dot",
            color="green",
            label="Single service",
        )

    if data["multi_dates"]:
        plt.scatter(
            data["multi_dates"],
            data["multi_mileages"],
            marker="hd",
            color="yellow",
            label="Multi service",
        )

    plt.title(f"{vehicle.car.name} — Mileage Over Time")
    plt.xlabel("Date")
    plt.ylabel("Miles")
    plt.show()
    return 0
```

- [ ] **Step 2: Add chart subparser**

In the `main()` function, add after the `rules_delete_parser` section (around line 1381, before `args = parser.parse_args()`):

```python
    # Chart subcommand
    chart_parser = subparsers.add_parser(
        "chart",
        help="Show mileage over time with service markers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s vehicles/wrx.yaml chart
  %(prog)s vehicles/wrx.yaml chart --rule oil
""",
    )
    chart_parser.add_argument(
        "--rule",
        type=str,
        help="Filter service markers to rules containing text (case-insensitive)",
    )
```

- [ ] **Step 3: Add dispatch**

In the dispatch section of `main()` (around line 1418), add before the final `return 0`:

```python
    elif args.command == "chart":
        return cmd_chart(args)
```

- [ ] **Step 4: Add tests for cmd_chart error messages**

Add to `tests/test_maint.py`, after the `TestExtractChartData` class. These test the error message paths without needing plotext:

```python
class TestCmdChartEdgeCases:
    """Tests for cmd_chart error message selection."""

    def _make_vehicle(self, history=None):
        car = Car(
            make="Test",
            model="Car",
            trim=None,
            year=2020,
            purchase_date="2020-01-01",
            purchase_miles=100,
        )
        return Vehicle(car=car, rules=[], history=history or [])

    def test_no_history_message(self, capsys, tmp_path):
        """No history at all -> 'No mileage data to chart.'"""
        from maint import cmd_chart
        import argparse

        # Create a minimal vehicle YAML
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(
            "car:\n  make: Test\n  model: Car\n  trim: Base\n"
            "  year: 2020\n  purchaseDate: '2020-01-01'\n  purchaseMiles: 100\n"
            "history: []\nrules: []\n"
        )
        args = argparse.Namespace(vehicle_file=yaml_path, rule=None)
        result = cmd_chart(args)
        assert result == 0
        assert "No mileage data to chart." in capsys.readouterr().out

    def test_only_null_mileage_message(self, capsys, tmp_path):
        """History entries but all mileage=None -> 'No mileage data to chart.'"""
        from maint import cmd_chart
        import argparse

        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(
            "car:\n  make: Test\n  model: Car\n  trim: Base\n"
            "  year: 2020\n  purchaseDate: '2020-01-01'\n  purchaseMiles: 100\n"
            "history:\n- ruleKey: oil/replace\n  date: '2020-06-01'\n"
            "rules: []\n"
        )
        args = argparse.Namespace(vehicle_file=yaml_path, rule=None)
        result = cmd_chart(args)
        assert result == 0
        assert "No mileage data to chart." in capsys.readouterr().out
```

Also update the imports at the top of `tests/test_maint.py` to include `cmd_chart`:

```python
from maint import (
    format_miles,
    format_cost,
    format_remaining,
    format_time_remaining,
    truncate,
    make_status_table,
    make_history_table,
    extract_chart_data,
    cmd_chart,
)
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_maint.py::TestCmdChartEdgeCases -v`
Expected: Both tests PASS.

- [ ] **Step 6: Manual test with real data**

Run: `uv run python maint.py vehicles/wrx.yaml chart`
Expected: ASCII chart showing mileage progression from ~0 to ~105k over 2012-2026 with service markers.

Run: `uv run python maint.py vehicles/wrx.yaml chart --rule oil`
Expected: Same line, but only oil-related service markers shown.

- [ ] **Step 7: Run full test suite**

Run: `mise run test-unit`
Expected: All tests pass (including new TestExtractChartData and TestCmdChartEdgeCases tests).

- [ ] **Step 8: Commit**

```bash
git add maint.py
git commit -m "add chart CLI command"
```

---

## Chunk 2: Web Chart Feature

### Task 4: Web chart data helpers and sparkline on History tab

**Files:**
- Modify: `web/app.py` (add helpers, update history route)
- Create: `web/templates/partials/mileage_sparkline.html`
- Modify: `web/templates/history.html` (include sparkline partial)

- [ ] **Step 1: Add chart data helper functions to web/app.py**

Add these two functions to `web/app.py`, near the top after imports and before routes (after the Jinja2 filter registrations):

```python
def _build_mileage_points(vehicle):
    """Build mileage timeline data for sparkline and chart."""
    points = {(vehicle.car.purchase_date, vehicle.car.purchase_miles)}
    for entry in vehicle.history:
        if entry.mileage is not None:
            points.add((entry.date, entry.mileage))
    sorted_points = sorted(points, key=lambda p: p[0])
    return [{"x": d, "y": m} for d, m in sorted_points]


def _build_service_markers(vehicle):
    """Build grouped service markers for chart."""
    from collections import defaultdict

    groups = defaultdict(list)
    for entry in vehicle.history:
        if entry.mileage is not None:
            groups[(entry.date, entry.mileage)].append(entry.rule_key)
    markers = []
    for (date, miles), services in sorted(groups.items()):
        markers.append({
            "x": date,
            "y": miles,
            "services": services,
            "count": len(services),
        })
    return markers
```

- [ ] **Step 2: Update history route to pass sparkline data**

In the `vehicle_history` function in `web/app.py` (around line 563), add before the `return render_template(...)` call:

```python
    mileage_points = _build_mileage_points(vehicle)
```

Then add `mileage_points=mileage_points,` to the `render_template()` call's keyword arguments.

- [ ] **Step 3: Create sparkline partial template**

Create `web/templates/partials/mileage_sparkline.html`:

```html
{% if mileage_points and mileage_points | length >= 2 %}
<a href="{{ url_for('vehicle_chart', vehicle_id=vehicle_id) }}"
   class="block mb-4 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 transition-colors">
    <div class="flex justify-between items-center mb-1">
        <span class="text-xs text-gray-500 dark:text-gray-400">Mileage Over Time</span>
        <span class="text-xs text-blue-500">View full chart &rarr;</span>
    </div>
    <div style="height: 48px;">
        <canvas id="sparkline-chart"></canvas>
    </div>
    <div class="flex justify-between text-xs text-gray-400 dark:text-gray-500 mt-1">
        <span>{{ mileage_points[0]['x'][:4] }}</span>
        <span>{{ mileage_points[-1]['y'] | format_miles }} mi</span>
    </div>
</a>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/date-fns@3"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
<script>
(function() {
    const ctx = document.getElementById('sparkline-chart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                data: {{ mileage_points | tojson }},
                borderColor: '#3b82f6',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0.1,
                fill: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            events: [],
            scales: {
                x: { type: 'time', display: false },
                y: { display: false },
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
        },
    });
})();
</script>
{% endif %}
```

- [ ] **Step 4: Include sparkline in history.html**

In `web/templates/history.html`, add the sparkline include after the filter/summary form (after the closing `</form>` tag of `id="filter-form"`, before the `<div class="space-y-1.5">` accordion container):

```html
{% include "partials/mileage_sparkline.html" %}
```

- [ ] **Step 5: Verify sparkline renders**

Run: `mise run serve`
Navigate to any vehicle's History tab. Expected: a compact blue sparkline card appears above the history entries, showing "Mileage Over Time" with start year and current mileage labels.

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/templates/partials/mileage_sparkline.html web/templates/history.html
git commit -m "add mileage sparkline to history tab"
```

---

### Task 5: Full chart page route and template

**Files:**
- Modify: `web/app.py` (add chart route)
- Create: `web/templates/chart.html`

- [ ] **Step 1: Add chart route to web/app.py**

Add a new route function in `web/app.py` (near the history route):

```python
@app.route("/vehicle/<vehicle_id>/chart")
def vehicle_chart(vehicle_id: str):
    """Full mileage chart page."""
    path = get_vehicle_path(vehicle_id)
    if not path.exists():
        flash(f"Vehicle '{vehicle_id}' not found", "error")
        return redirect(url_for("index"))

    vehicle = load_vehicle(path)
    mileage_points = _build_mileage_points(vehicle)
    service_markers = _build_service_markers(vehicle)

    all_status = vehicle.get_all_service_status(severe=False)
    status_counts = {
        "overdue": sum(1 for s in all_status if s.status == Status.OVERDUE),
        "due_soon": sum(1 for s in all_status if s.status == Status.DUE_SOON),
        "ok": sum(1 for s in all_status if s.status == Status.OK),
    }

    return render_template(
        "chart.html",
        vehicle_id=vehicle_id,
        vehicle=vehicle,
        mileage_points=mileage_points,
        service_markers=service_markers,
        status_counts=status_counts,
        active_tab="history",
    )
```

Note: `active_tab="history"` keeps the History tab highlighted since the chart is accessed from there.

- [ ] **Step 2: Create chart.html template**

Create `web/templates/chart.html`:

```html
{% extends "vehicle_base.html" %}

{% block title %}{{ vehicle.car.name }} - Mileage Chart{% endblock %}

{% block tab_content %}
<!-- Filter bar -->
<div class="mb-4 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
    <div class="flex items-center gap-3">
        <a href="{{ url_for('vehicle_history', vehicle_id=vehicle_id) }}"
           class="text-sm text-blue-500 hover:text-blue-600 whitespace-nowrap">&larr; Back to history</a>
        <input type="text"
               id="rule-filter"
               placeholder="Filter services (e.g., oil, tires)..."
               class="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded text-sm text-gray-900 dark:text-gray-100">
    </div>
</div>

<!-- Chart container -->
<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
     style="height: 400px;">
    <canvas id="mileage-chart"></canvas>
</div>

<!-- Legend -->
<div class="flex gap-4 mt-3 text-sm text-gray-600 dark:text-gray-400">
    <span class="flex items-center gap-1">
        <span class="inline-block w-3 h-3 rounded-full bg-green-500"></span>
        Single service
    </span>
    <span class="flex items-center gap-1">
        <span class="inline-block w-3 h-3 rounded-full bg-amber-500"></span>
        Multiple services
    </span>
</div>

<!-- Chart.js CDN -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/date-fns@3"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>

<script>
(function() {
    const isDark = document.documentElement.classList.contains('dark');
    const textColor = isDark ? '#e2e8f0' : '#1e293b';
    const gridColor = isDark ? '#334155' : '#e2e8f0';

    const mileagePoints = {{ mileage_points | tojson }};
    const serviceMarkers = {{ service_markers | tojson }};

    const singleMarkers = serviceMarkers.filter(m => m.count === 1);
    const multiMarkers = serviceMarkers.filter(m => m.count > 1);

    const ctx = document.getElementById('mileage-chart').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'Mileage',
                    data: mileagePoints,
                    borderColor: '#3b82f6',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.1,
                    fill: false,
                },
                {
                    label: 'Single service',
                    data: singleMarkers,
                    type: 'scatter',
                    backgroundColor: '#22c55e',
                    pointRadius: 5,
                },
                {
                    label: 'Multiple services',
                    data: multiMarkers,
                    type: 'scatter',
                    backgroundColor: '#f59e0b',
                    pointRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'year' },
                    ticks: { color: textColor },
                    grid: { color: gridColor },
                },
                y: {
                    ticks: {
                        color: textColor,
                        callback: function(v) { return v.toLocaleString(); },
                    },
                    grid: { color: gridColor },
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: function(items) {
                            var item = items[0];
                            var d = new Date(item.parsed.x);
                            return d.toLocaleDateString('en-US', {year: 'numeric', month: 'short', day: 'numeric'})
                                   + ' \u2014 ' + item.parsed.y.toLocaleString() + ' mi';
                        },
                        label: function(context) {
                            if (context.datasetIndex === 0) return '';
                            var services = context.raw.services;
                            if (services) return services.map(function(s) { return '\u2022 ' + s; });
                            return '';
                        },
                    },
                },
            },
        },
    });

    // Client-side filtering
    var allSingleMarkers = singleMarkers.slice();
    var allMultiMarkers = multiMarkers.slice();

    document.getElementById('rule-filter').addEventListener('input', function(e) {
        var filter = e.target.value.toLowerCase();
        if (!filter) {
            chart.data.datasets[1].data = allSingleMarkers;
            chart.data.datasets[2].data = allMultiMarkers;
        } else {
            // Recount matched services per point so single/multi classification updates
            var filtered = serviceMarkers.map(function(m) {
                var matched = m.services.filter(function(s) {
                    return s.toLowerCase().indexOf(filter) !== -1;
                });
                return matched.length > 0
                    ? {x: m.x, y: m.y, services: matched, count: matched.length}
                    : null;
            }).filter(function(m) { return m !== null; });
            chart.data.datasets[1].data = filtered.filter(function(m) { return m.count === 1; });
            chart.data.datasets[2].data = filtered.filter(function(m) { return m.count > 1; });
        }
        chart.update();
    });
})();
</script>
{% endblock %}
```

- [ ] **Step 3: Verify chart page renders**

Run: `mise run serve`
Navigate to History tab, click the sparkline card. Expected: full chart page loads at `/vehicle/<id>/chart` showing the mileage line with green/amber service markers. The filter input and legend are visible. Hovering over markers shows a tooltip with date, mileage, and service names.

- [ ] **Step 4: Verify dark mode**

Toggle dark mode on the chart page. Expected: reload shows chart with light text on dark background. Grid lines are subtle dark gray.

- [ ] **Step 5: Run format and lint**

Run: `mise run format && mise run lint`
Expected: No errors. Fix any issues before committing.

- [ ] **Step 6: Commit**

```bash
git add web/app.py web/templates/chart.html
git commit -m "add full mileage chart page"
```

---

### Task 6: E2E tests for sparkline and chart page

**Files:**
- Modify: `tests/e2e/test_history.py` (add sparkline/chart tests)

The e2e test fixture (`tests/e2e/fixtures/test_vehicle.yaml`) has `purchaseDate: '2020-01-01'`, `purchaseMiles: 0`, and 2 history entries with mileage (10000 and 8500). That gives 3 data points — enough for the sparkline to render.

- [ ] **Step 1: Add sparkline visibility test**

Add to `tests/e2e/test_history.py`:

```python
@pytest.mark.e2e
def test_sparkline_visible_on_history(page, flask_server):
    """Sparkline card appears on history tab when mileage data exists."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    sparkline = page.locator("#sparkline-chart")
    assert sparkline.count() == 1
    # Check the "View full chart" link is present
    assert "View full chart" in page.content()
```

- [ ] **Step 2: Add chart page navigation test**

```python
@pytest.mark.e2e
def test_sparkline_links_to_chart(page, flask_server):
    """Clicking sparkline navigates to chart page."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    page.locator("a:has(#sparkline-chart)").click()
    page.wait_for_url("**/chart")
    assert "/vehicle/test_vehicle/chart" in page.url
    # Chart canvas should be present
    assert page.locator("#mileage-chart").count() == 1
```

- [ ] **Step 3: Add chart page filter test**

```python
@pytest.mark.e2e
def test_chart_filter_input_exists(page, flask_server):
    """Chart page has a filter input and legend."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/chart")
    assert page.locator("#rule-filter").count() == 1
    assert "Single service" in page.content()
    assert "Multiple services" in page.content()
```

- [ ] **Step 4: Add back-to-history link test**

```python
@pytest.mark.e2e
def test_chart_back_to_history(page, flask_server):
    """Chart page has a back link to history."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/chart")
    page.get_by_text("Back to history").click()
    page.wait_for_url("**/history")
    assert "/vehicle/test_vehicle/history" in page.url
```

- [ ] **Step 5: Run e2e tests**

Run: `mise run test-web`
Expected: All new and existing e2e tests pass.

- [ ] **Step 6: Run full CI suite**

Run: `mise run test`
Expected: All checks pass (format, lint, validate, unit tests, web tests).

- [ ] **Step 7: Commit**

```bash
git add tests/e2e/test_history.py
git commit -m "add e2e tests for sparkline and chart page"
```
