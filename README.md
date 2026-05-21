# superinstance-runtime

Universal event bus with a three-phase pipeline: **COLLECT → SELECT → COMPILE**.

## What it is

An event bus where every cycle follows the same structure:

1. **COLLECT** — Gather raw events from registered collectors
2. **SELECT** — Filter events through threshold-based selectors
3. **COMPILE** — Aggregate selected events into results

That's it. No magic. The universality comes from the plugin system — any domain (constraints, PLATO tiles, fleet health, telemetry) plugs in by providing collectors, selectors, and compilers.

## Why it's universal

The COLLECT→SELECT→COMPILE pattern maps to any event-processing domain:

| Domain | Collect | Select | Compile |
|--------|---------|--------|---------|
| Constraint checking | Read current values | Filter violations | Summarize violations |
| PLATO tiles | Read tile states | Filter by confidence | Rank by relevance |
| Fleet health | Poll agent health | Filter above threshold | Aggregate status |
| Telemetry | Gather metrics | Filter anomalies | Build dashboard data |
| Regime transitions | Detect state changes | Threshold crossing | Record transition |

In production use, this bus has processed **141 proven regime transitions** without architecture changes — the same three-phase pipeline handles every domain.

## Install

```bash
pip install superinstance-runtime
```

## Quick start

```python
from superinstance_runtime.bus import EventBus
from superinstance_runtime.registry import PluginRegistry

# Create the bus
bus = EventBus()

# Register components directly
bus.register_collector("sensor", lambda: [
    {"type": "reading", "sensor": "temp", "value": 72.3},
    {"type": "reading", "sensor": "pressure", "value": 14.7},
])

bus.register_selector(
    "high_temp",
    lambda event, threshold: (
        event.get("type") == "reading"
        and event.get("sensor") == "temp"
        and event.get("value", 0) > threshold
    ),
    threshold=70.0,
)

bus.register_compiler("alert", lambda events: {
    "type": "alert",
    "count": len(events),
    "readings": events,
})

# Run a cycle
result = bus.run_cycle()
print(f"Collected: {result.collected}")  # 2 events
print(f"Selected:  {result.selected}")   # 1 event (temp > 70)
print(f"Compiled:  {result.compiled}")   # 1 result (alert)
```

## Plugin example

```python
from superinstance_runtime.bus import EventBus
from superinstance_runtime.registry import PluginRegistry
from superinstance_runtime.plugins.constraint import (
    make_constraint_collector,
    constraint_selector,
    constraint_compiler,
)

bus = EventBus()
registry = PluginRegistry()

# Define a constraint plugin
registry.register_plugin(
    name="constraints",
    collectors={
        "check": make_constraint_collector(
            values={"speed": 85.0, "temperature": 42.0},
            bounds={"speed": (0, 80), "temperature": (0, 100)},
        ),
    },
    selectors={"violation": (constraint_selector, 1.0)},
    compilers={"summary": constraint_compiler},
)

# Load plugin into bus
registry.load_plugins(bus)

# Run cycle — speed is over the limit
result = bus.run_cycle()
print(result.results[0])
# {'type': 'constraint_summary', 'violation_count': 1,
#  'violations': [{'name': 'speed', 'value': 85.0, 'bounds': (0, 80)}]}
```

## Architecture

```
          ┌───────────────────────────────────────────────┐
          │              PluginRegistry                    │
          │                                               │
          │  register_plugin(name, collectors,            │
          │                   selectors, compilers)        │
          └───────────────────┬───────────────────────────┘
                              │ load_plugins()
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                        EventBus                               │
│                                                               │
│   COLLECT              SELECT                COMPILE          │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────┐      │
│  │collector₁│     │ selector₁    │     │  compiler₁   │      │
│  │collector₂│ ──▶ │ selector₂    │ ──▶ │  compiler₂   │ ──▶  │
│  │collector₃│     │ selector₃    │     │  compiler₃   │      │
│  └──────────┘     └──────────────┘     └──────────────┘      │
│                                                               │
│   run_cycle() → CycleResult(collected, selected, compiled)    │
└───────────────────────────────────────────────────────────────┘
```

## Built-in plugins

### `constraint` — Constraint checking

| Component | Description |
|-----------|-------------|
| `make_constraint_collector(values, bounds)` | Yields constraint-check events |
| `constraint_selector(event, threshold)` | Passes violated constraints |
| `constraint_compiler(events)` | Summarizes violations |

### `plato` — PLATO tile processing

| Component | Description |
|-----------|-------------|
| `make_tile_collector(tiles)` | Yields tile-read events |
| `tile_confidence_selector(event, threshold)` | Passes tiles above confidence threshold |
| `make_tile_compiler(top_k)` | Compiles top-K tiles by relevance |

## Writing a custom plugin

A plugin is three callables registered under a name:

```python
# my_plugin.py

def make_my_collector(data_source):
    def collect():
        return [{"type": "my_event", "value": v} for v in data_source()]
    return collect

def my_selector(event, threshold=0.5):
    return event.get("type") == "my_event" and event["value"] > threshold

def my_compiler(events):
    return {"type": "my_result", "total": sum(e["value"] for e in events)}
```

```python
# Usage
registry.register_plugin(
    name="my_plugin",
    collectors={"main": make_my_collector(lambda: [0.3, 0.7, 0.9])},
    selectors={"filter": (my_selector, 0.5)},
    compilers={"aggregate": my_compiler},
)
registry.load_plugins(bus)
result = bus.run_cycle()
```

## Running tests

```bash
pip install pytest
pytest tests/
```

## License

MIT
