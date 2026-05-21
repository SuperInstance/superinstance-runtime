"""Integration tests: full pipeline with constraint + PLATO plugins."""

import pytest

from superinstance_runtime.bus import EventBus
from superinstance_runtime.registry import PluginRegistry
from superinstance_runtime.plugins.constraint import (
    make_constraint_collector,
    constraint_selector,
    constraint_compiler,
)
from superinstance_runtime.plugins.plato import (
    make_tile_collector,
    tile_confidence_selector,
    make_tile_compiler,
)


class TestConstraintPlugin:
    def test_all_within_bounds(self):
        bus = EventBus()
        bus.register_collector(
            "constraint",
            make_constraint_collector(
                {"x": 1.0, "y": 5.0},
                {"x": (0.0, 2.0), "y": (0.0, 10.0)},
            ),
        )
        bus.register_selector("constraint", constraint_selector)
        bus.register_compiler("constraint", constraint_compiler)
        result = bus.run_cycle()
        assert result.collected == 2
        assert result.selected == 0  # none violated
        summary = result.results[0]
        assert summary["violation_count"] == 0

    def test_violations_detected(self):
        bus = EventBus()
        bus.register_collector(
            "constraint",
            make_constraint_collector(
                {"x": 5.0, "y": -1.0},
                {"x": (0.0, 2.0), "y": (0.0, 10.0)},
            ),
        )
        bus.register_selector("constraint", constraint_selector)
        bus.register_compiler("constraint", constraint_compiler)
        result = bus.run_cycle()
        assert result.collected == 2
        assert result.selected == 2  # both violated
        summary = result.results[0]
        assert summary["violation_count"] == 2


class TestPlatoPlugin:
    def test_tile_filtering(self):
        tiles = [
            {"id": "t1", "confidence": 0.9, "relevance": 0.8, "content": "a"},
            {"id": "t2", "confidence": 0.2, "relevance": 0.1, "content": "b"},
            {"id": "t3", "confidence": 0.7, "relevance": 0.6, "content": "c"},
        ]
        bus = EventBus()
        bus.register_collector("plato", make_tile_collector(tiles))
        bus.register_selector("plato", tile_confidence_selector, threshold=0.5)
        bus.register_compiler("plato", make_tile_compiler(top_k=2))
        result = bus.run_cycle()
        assert result.collected == 3
        assert result.selected == 2  # t1 and t3 pass threshold
        compiled = result.results[0]
        assert compiled["top_k"] == 2
        assert len(compiled["tiles"]) == 2
        # sorted by relevance desc
        assert compiled["tiles"][0]["tile_id"] == "t1"

    def test_all_below_threshold(self):
        tiles = [{"id": "t1", "confidence": 0.1, "relevance": 0.1}]
        bus = EventBus()
        bus.register_collector("plato", make_tile_collector(tiles))
        bus.register_selector("plato", tile_confidence_selector, threshold=0.5)
        bus.register_compiler("plato", make_tile_compiler())
        result = bus.run_cycle()
        assert result.collected == 1
        assert result.selected == 0


class TestFullIntegration:
    def test_both_plugins_together(self):
        """Constraint + PLATO in the same bus cycle."""
        bus = EventBus()

        # constraint plugin
        bus.register_collector(
            "constraint",
            make_constraint_collector({"a": 100.0}, {"a": (0.0, 10.0)}),
        )
        bus.register_selector("constraint", constraint_selector)
        bus.register_compiler("constraint", constraint_compiler)

        # plato plugin
        tiles = [{"id": "p1", "confidence": 0.9, "relevance": 0.8}]
        bus.register_collector("plato", make_tile_collector(tiles))
        bus.register_selector("plato", tile_confidence_selector, threshold=0.5)
        bus.register_compiler("plato", make_tile_compiler(top_k=3))

        result = bus.run_cycle()
        assert result.collected == 2  # 1 constraint + 1 tile
        assert result.selected == 2  # both pass their selectors
        assert result.compiled == 2  # 2 compilers

    def test_via_plugin_registry(self):
        """Load plugins through PluginRegistry."""
        bus = EventBus()
        registry = PluginRegistry()

        registry.register_plugin(
            "constraint",
            collectors={"checks": make_constraint_collector({"x": -5.0}, {"x": (0.0, 1.0)})},
            selectors={"violations": (constraint_selector, 1.0)},
            compilers={"summary": constraint_compiler},
        )

        registry.register_plugin(
            "plato",
            collectors={"tiles": make_tile_collector([{"id": "z", "confidence": 0.8, "relevance": 0.5}])},
            selectors={"confidence": (tile_confidence_selector, 0.5)},
            compilers={"top": make_tile_compiler(top_k=5)},
        )

        registry.load_plugins(bus)
        result = bus.run_cycle()
        assert result.collected == 2
        assert result.compiled == 2

    def test_threshold_tuning(self):
        """Adjusting threshold changes selection count."""
        tiles = [
            {"id": "a", "confidence": 0.3},
            {"id": "b", "confidence": 0.6},
            {"id": "c", "confidence": 0.9},
        ]

        # low threshold → 2 pass
        bus_low = EventBus()
        bus_low.register_collector("plato", make_tile_collector(tiles))
        bus_low.register_selector("plato", tile_confidence_selector, threshold=0.5)
        bus_low.register_compiler("plato", make_tile_compiler())
        r_low = bus_low.run_cycle()
        assert r_low.selected == 2

        # high threshold → 1 pass
        bus_high = EventBus()
        bus_high.register_collector("plato", make_tile_collector(tiles))
        bus_high.register_selector("plato", tile_confidence_selector, threshold=0.8)
        bus_high.register_compiler("plato", make_tile_compiler())
        r_high = bus_high.run_cycle()
        assert r_high.selected == 1

    def test_consecutive_cycles(self):
        """Multiple cycles on the same bus produce independent results."""
        call_count = 0

        def counting_collector():
            nonlocal call_count
            call_count += 1
            return [{"val": call_count}]

        bus = EventBus()
        bus.register_collector("c", counting_collector)
        bus.register_selector("s", _always_select_fn)
        bus.register_compiler("comp", _count_compiler_fn)

        r1 = bus.run_cycle()
        r2 = bus.run_cycle()
        assert r1.collected == 1
        assert r2.collected == 1
        assert r1.results != r2.results  # different data per cycle


def _always_select_fn(event, threshold=0.0):
    return True


def _count_compiler_fn(events):
    return {"count": len(events), "vals": [e.get("val") for e in events]}
