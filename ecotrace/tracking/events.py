"""Event handling for the tracking layer."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

# Type alias for event handler callbacks
EventHandler = Callable[[str, Dict[str, Any]], None]


class EventEmitter:
    """Simple event emitter for tracking lifecycle hooks.

    Allows components to subscribe to events like 'before_track',
    'after_track', 'on_duplicate', etc.
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}

    def on(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for an event.

        Args:
            event_name: Name of the event to listen for.
            handler: Callable(event_name, data_dict).
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def off(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        if event_name in self._handlers:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name] if h is not handler
            ]

    def emit(self, event_name: str, data: Dict[str, Any] | None = None) -> None:
        """Emit an event, calling all registered handlers."""
        for handler in self._handlers.get(event_name, []):
            handler(event_name, data or {})

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
