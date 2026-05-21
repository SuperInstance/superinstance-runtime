"""PLATO tile plugin: generates tile-read events."""

from __future__ import annotations


# ── Collector ──────────────────────────────────────────────────────

def make_tile_collector(tiles: list[dict]):
    """Return a collector that yields tile-read events.

    Each tile dict should have at least ``confidence`` and ``relevance`` keys.
    """

    def collect() -> list[dict]:
        return [
            {
                "type": "tile_read",
                "tile_id": t.get("id", idx),
                "confidence": t.get("confidence", 0.0),
                "relevance": t.get("relevance", 0.0),
                "content": t.get("content", ""),
            }
            for idx, t in enumerate(tiles)
        ]

    return collect


# ── Selector ───────────────────────────────────────────────────────

def tile_confidence_selector(event: dict, threshold: float = 0.5) -> bool:
    """Pass tile events with confidence > *threshold*."""
    return event.get("type") == "tile_read" and event.get("confidence", 0.0) > threshold


# ── Compiler ───────────────────────────────────────────────────────

def make_tile_compiler(top_k: int = 5):
    """Return a compiler that picks the top-K tiles by relevance."""

    def compile_tiles(events: list[dict]) -> dict:
        tiles = [e for e in events if e.get("type") == "tile_read"]
        tiles.sort(key=lambda e: e.get("relevance", 0.0), reverse=True)
        top = tiles[:top_k]
        return {
            "type": "tile_compilation",
            "total": len(tiles),
            "top_k": top_k,
            "tiles": top,
        }

    return compile_tiles
