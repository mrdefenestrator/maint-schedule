# Design Notes

Architecture and key design decisions for the vehicle maintenance schedule system.

---

## Domain Model

The system is built around four core concepts:

- **Car** — static vehicle identity (make, model, year, purchase info)
- **Rule** — a maintenance interval definition (`item/verb`, optional `phase`)
- **HistoryEntry** — a log record of a service actually performed
- **Vehicle** — the aggregate: a car + its rules + its history, with computed status

Status is never stored. It is always computed at read time from the current mileage, the current date, and the service history.

---

## Rule Identity: Natural Keys

Rules are identified by a natural key of the form `item/verb` or `item/verb/phase`:

```
engine oil and filter/replace
engine coolant/replace/initial
engine coolant/replace/ongoing
```

History entries reference these keys in the `ruleKey` field. The `item` and `verb` fields are free-form strings — the system does not enumerate or validate them, which keeps the rule vocabulary open for any vehicle or maintenance style.

---

## Service Due Calculation

### Fresh-at-zero assumption

If no history exists for a rule, the system assumes the item was serviced at odometer 0 (or at `startMiles` for rules with a start threshold). The first service is due at `startMiles + intervalMiles`.

### Service-based intervals

After a service is logged, the next due point is calculated from when the service was *actually* performed, not when it was scheduled. This prevents intervals from drifting forward when a service is done early or late.

### Whichever comes first

When a rule has both a mileage interval and a time interval, the service is due when *either* threshold is crossed. The status escalates to the worse of the two.

### Severe mode

Rules can define separate severe intervals (`severeIntervalMiles`, `severeIntervalMonths`) for demanding driving conditions. In severe mode the severe interval is used; it falls back to the normal interval if no severe interval is defined.

---

## Lifecycle Rules (Phases)

Some maintenance items have different intervals at different points in a vehicle's life. The `phase` field (`initial` or `ongoing`) distinguishes them while keeping the `item/verb` pairing intact:

```yaml
- item: engine coolant
  verb: replace
  phase: initial
  intervalMiles: 137500
  stopMiles: 137500

- item: engine coolant
  verb: replace
  phase: ongoing
  intervalMiles: 75000
  startMiles: 137500
```

When looking up service history, the system matches on **item + verb only**, ignoring phase. This lets lifecycle phases hand off correctly: history logged under `engine coolant/replace/initial` is found and used by the `ongoing` rule to calculate the next due point.

---

## `countsAs`: Cross-Verb History Satisfaction

A rule can declare that its service history also satisfies other verbs for the same item, using the `countsAs` field:

```yaml
- item: engine air filter
  verb: replace
  intervalMiles: 15000
  countsAs: [inspect]

- item: engine air filter
  verb: inspect
  intervalMiles: 7500
```

With this configuration, logging a `replace` service also resets the `inspect` interval. When the system calculates the due date for `engine air filter/inspect`, it looks up history for `engine air filter/replace` as well (because that rule declares `countsAs: [inspect]`), and uses whichever service is most recent.

### Design rationale

- **Opt-in, per-rule** — `countsAs` is an empty list by default. No behavior changes unless explicitly configured. Rules without it are unaffected.
- **Declared on the source rule** — the rule doing the satisfying carries the declaration (`replace` says "I also count as inspect"), which reads naturally: "replacing the filter counts as inspecting it."
- **Scoped to the same item** — cross-item satisfaction is not supported. `countsAs` only matches rules on the same `item`, preventing unintended interactions.
- **Multiple verbs** — `countsAs` is a list, so a single rule can satisfy multiple verbs if needed (e.g., `countsAs: [inspect, clean]`).

### History resolution with `countsAs`

The lookup in `Vehicle.get_last_service_for_item` follows this order:

1. Collect all history entries whose `ruleKey` starts with `item/verb` (direct match, any phase)
2. Scan all rules for same-item rules whose `countsAs` includes the requested verb; collect their history entries too
3. From the combined set, prefer entries with mileage; return the most recent

---

## Aftermarket Parts

Parts added after purchase use `startMiles` to indicate when they were installed. The rule is `INACTIVE` below that threshold and the first service is due at `startMiles + intervalMiles` once active.

The `aftermarket: true` flag is informational — it has no effect on calculation logic, but it distinguishes non-OEM items in display and reporting.

---

## YAML as the Data Store

Vehicle data lives in YAML files rather than a database. This was a deliberate choice:

- Files are human-readable and hand-editable
- No migration machinery required
- Easy to version-control alongside the codebase
- Trivial to back up or share

The trade-off is that concurrent writes are not safe, and there is no query capability beyond loading the full file. For a single-user tool managing a small fleet, these are acceptable constraints.

`None` values are omitted on write to keep the YAML clean and diff-friendly.
