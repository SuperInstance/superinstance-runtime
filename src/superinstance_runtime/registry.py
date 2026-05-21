"""Plugin registry for the event bus."""

from __future__ import annotations

from dataclasses import dataclass, field

from .bus import EventBus


@dataclass
class PluginDefinition:
    """A plugin's registered components."""

    name: str
    collectors: dict[str, object] = field(default_factory=dict)
    selectors: dict[str, tuple[object, float]] = field(default_factory=dict)
    compilers: dict[str, object] = field(default_factory=dict)


class PluginRegistry:
    """Discovers and loads plugins into an EventBus."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginDefinition] = {}

    def register_plugin(
        self,
        name: str,
        collectors: dict[str, object] | None = None,
        selectors: dict[str, tuple[object, float]] | None = None,
        compilers: dict[str, object] | None = None,
    ) -> None:
        """Register a plugin by name with its component callables."""
        self._plugins[name] = PluginDefinition(
            name=name,
            collectors=collectors or {},
            selectors=selectors or {},
            compilers=compilers or {},
        )

    def load_plugins(self, bus: EventBus) -> None:
        """Load all registered plugins into the given bus."""
        for plugin in self._plugins.values():
            for cname, fn in plugin.collectors.items():
                bus.register_collector(f"{plugin.name}.{cname}", fn)
            for sname, (fn, threshold) in plugin.selectors.items():
                bus.register_selector(f"{plugin.name}.{sname}", fn, threshold)
            for compname, fn in plugin.compilers.items():
                bus.register_compiler(f"{plugin.name}.{compname}", fn)

    @property
    def plugin_names(self) -> list[str]:
        return list(self._plugins.keys())
