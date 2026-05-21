"""Constraint-checking plugin: generates violation events."""

from __future__ import annotations


# ── Collector ──────────────────────────────────────────────────────

def make_constraint_collector(values: dict[str, float], bounds: dict[str, tuple[float, float]]):
    """Return a collector that yields constraint-check events.

    *values*: ``{name: current_value}``
    *bounds*: ``{name: (lo, hi)}``
    """

    def collect() -> list[dict]:
        events = []
        for name, value in values.items():
            if name in bounds:
                lo, hi = bounds[name]
                events.append({
                    "type": "constraint_check",
                    "name": name,
                    "value": value,
                    "lo": lo,
                    "hi": hi,
                    "violated": not (lo <= value <= hi),
                })
        return events

    return collect


# ── Selector ───────────────────────────────────────────────────────

def constraint_selector(event: dict, threshold: float = 1.0) -> bool:
    """Pass events where *violated* is True (threshold unused, kept for API compat)."""
    return event.get("type") == "constraint_check" and event.get("violated", False)


# ── Compiler ───────────────────────────────────────────────────────

def constraint_compiler(events: list[dict]) -> dict:
    """Summarise violated constraints."""
    violated = [e for e in events if e.get("type") == "constraint_check" and e.get("violated")]
    return {
        "type": "constraint_summary",
        "violation_count": len(violated),
        "violations": [
            {"name": e["name"], "value": e["value"], "bounds": (e["lo"], e["hi"])}
            for e in violated
        ],
    }
