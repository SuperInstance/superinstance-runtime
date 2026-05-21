"""Event bus implementing COLLECT → SELECT → COMPILE pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CycleResult:
    """Result of a single bus cycle."""

    collected: int = 0
    selected: int = 0
    compiled: int = 0
    results: list = field(default_factory=list)


class EventBus:
    """Three-phase event bus: COLLECT → SELECT → COMPILE.

    Collectors gather raw events.
    Selectors filter events by threshold criteria.
    Compilers aggregate selected events into results.
    """

    def __init__(self) -> None:
        self._collectors: list[tuple[str, object]] = []
        self._selectors: list[tuple[str, object, float]] = []
        self._compilers: list[tuple[str, object]] = []

    # ── registration ──────────────────────────────────────────────

    def register_collector(self, name: str, fn: object) -> None:
        """Register a collector. *fn* takes no args, returns a list of events."""
        self._collectors.append((name, fn))

    def register_selector(self, name: str, fn: object, threshold: float = 0.0) -> None:
        """Register a selector. *fn(event) → bool*; passes *threshold*."""
        self._selectors.append((name, fn, threshold))

    def register_compiler(self, name: str, fn: object) -> None:
        """Register a compiler. *fn(selected_events) → result*."""
        self._compilers.append((name, fn))

    # ── cycle execution ───────────────────────────────────────────

    def run_cycle(self) -> CycleResult:
        """Run one full COLLECT → SELECT → COMPILE cycle."""
        # Phase 1: COLLECT
        collected: list = []
        for _name, fn in self._collectors:
            collected.extend(fn())

        # Phase 2: SELECT — each selector votes; event passes if ANY selector accepts
        selected: list = []
        for event in collected:
            for _name, fn, threshold in self._selectors:
                try:
                    if fn(event, threshold):
                        selected.append(event)
                        break
                except TypeError:
                    # selector doesn't take threshold — call with just event
                    if fn(event):
                        selected.append(event)
                        break

        # Phase 3: COMPILE
        results: list = []
        for _name, fn in self._compilers:
            results.append(fn(selected))

        return CycleResult(
            collected=len(collected),
            selected=len(selected),
            compiled=len(results),
            results=results,
        )
