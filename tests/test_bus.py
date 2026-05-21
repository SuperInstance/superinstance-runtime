"""Unit tests for the event bus."""

import pytest

from superinstance_runtime.bus import CycleResult, EventBus


# ── helpers ────────────────────────────────────────────────────────

def _noop_collector():
    return []


def _single_collector(event):
    def collect():
        return [event]
    return collect


def _always_select(event, threshold=0.0):
    return True


def _never_select(event, threshold=0.0):
    return False


def _identity_compiler(events):
    return events


def _count_compiler(events):
    return {"count": len(events)}


# ── tests ──────────────────────────────────────────────────────────

class TestRegistration:
    def test_register_collector(self):
        bus = EventBus()
        bus.register_collector("c1", _noop_collector)
        assert len(bus._collectors) == 1
        assert bus._collectors[0][0] == "c1"

    def test_register_selector(self):
        bus = EventBus()
        bus.register_selector("s1", _always_select, threshold=0.5)
        assert len(bus._selectors) == 1
        assert bus._selectors[0][2] == 0.5

    def test_register_compiler(self):
        bus = EventBus()
        bus.register_compiler("comp1", _identity_compiler)
        assert len(bus._compilers) == 1

    def test_multiple_collectors(self):
        bus = EventBus()
        for i in range(5):
            bus.register_collector(f"c{i}", _noop_collector)
        assert len(bus._collectors) == 5


class TestCycleResult:
    def test_empty_cycle(self):
        bus = EventBus()
        result = bus.run_cycle()
        assert result.collected == 0
        assert result.selected == 0
        assert result.compiled == 0
        assert result.results == []

    def test_collect_only(self):
        bus = EventBus()
        bus.register_collector("c1", _single_collector({"val": 42}))
        result = bus.run_cycle()
        assert result.collected == 1
        assert result.selected == 0  # no selectors → nothing passes

    def test_collect_and_select(self):
        bus = EventBus()
        bus.register_collector("c1", _single_collector({"val": 1}))
        bus.register_selector("s1", _always_select)
        result = bus.run_cycle()
        assert result.collected == 1
        assert result.selected == 1
        assert result.compiled == 0

    def test_full_pipeline(self):
        bus = EventBus()
        bus.register_collector("c1", _single_collector({"val": 99}))
        bus.register_selector("s1", _always_select)
        bus.register_compiler("comp1", _count_compiler)
        result = bus.run_cycle()
        assert result.collected == 1
        assert result.selected == 1
        assert result.compiled == 1
        assert result.results == [{"count": 1}]

    def test_selector_rejects(self):
        bus = EventBus()
        bus.register_collector("c1", _single_collector({"val": 1}))
        bus.register_selector("s1", _never_select)
        bus.register_compiler("comp1", _identity_compiler)
        result = bus.run_cycle()
        assert result.collected == 1
        assert result.selected == 0
        # compiler still runs, just gets empty list
        assert result.compiled == 1

    def test_multiple_collectors_accumulate(self):
        bus = EventBus()
        bus.register_collector("c1", lambda: [1, 2])
        bus.register_collector("c2", lambda: [3, 4, 5])
        bus.register_selector("s1", _always_select)
        bus.register_compiler("comp1", _count_compiler)
        result = bus.run_cycle()
        assert result.collected == 5
        assert result.selected == 5

    def test_cycle_result_dataclass(self):
        r = CycleResult(collected=10, selected=3, compiled=1, results=[{"ok": True}])
        assert r.collected == 10
        assert r.results == [{"ok": True}]

    def test_multiple_compilers(self):
        bus = EventBus()
        bus.register_collector("c1", lambda: [1])
        bus.register_selector("s1", _always_select)
        bus.register_compiler("comp1", _count_compiler)
        bus.register_compiler("comp2", _identity_compiler)
        result = bus.run_cycle()
        assert result.compiled == 2
        assert result.results[0] == {"count": 1}
        assert result.results[1] == [1]
