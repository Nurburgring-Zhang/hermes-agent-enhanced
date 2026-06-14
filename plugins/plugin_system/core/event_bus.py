"""
Hermes Plugin System - Event Bus
Central event bus for inter-plugin communication.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event data structure."""
    type: str
    source: str
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<Event type={self.type} source={self.source} time={self.timestamp.isoformat()}>"


class EventBus:
    """
    Central event bus for asynchronous inter-plugin communication.
    Supports pub/sub, event filtering, and priority handlers.
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._wildcard_subscribers: list[Callable] = []
        self._history: list[Event] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, source: str, data: Any = None, **kwargs) -> None:
        """
        Publish an event to all subscribers.
        Args:
            event_type: Event type string
            source: Source plugin/module name
            data: Event payload
            **kwargs: Additional metadata
        """
        event = Event(
            type=event_type,
            source=source,
            data=data,
            metadata=kwargs
        )

        async with self._lock:
            # Store in history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)

            # Get handlers for this event type
            handlers = list(self._subscribers[event_type])
            handlers.extend(self._wildcard_subscribers)

        # Execute handlers asynchronously
        tasks = []
        for handler in handlers:
            # Determine handler type (sync or async)
            if asyncio.iscoroutinefunction(handler):
                task = asyncio.create_task(self._safe_call_async(handler, event))
            else:
                task = asyncio.create_task(self._safe_call_sync(handler, event))
            tasks.append(task)

        # Wait for all tasks (non-blocking in batch context)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe(self, event_type: str, handler: Callable[[Event], Any]) -> None:
        """
        Subscribe to a specific event type.
        Args:
            event_type: Event type to listen for
            handler: Callback function (can be sync or async)
        """
        async with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"Subscribed to event: {event_type}")

    async def unsubscribe(self, event_type: str, handler: Callable[[Event], Any]) -> None:
        """
        Unsubscribe from an event type.
        Args:
            event_type: Event type
            handler: Handler to remove
        """
        async with self._lock:
            if handler in self._subscribers.get(event_type, []):
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed from event: {event_type}")

    async def subscribe_all(self, handler: Callable[[Event], Any]) -> None:
        """
        Subscribe to all events (wildcard).
        Args:
            handler: Callback for all events
        """
        async with self._lock:
            if handler not in self._wildcard_subscribers:
                self._wildcard_subscribers.append(handler)
                logger.debug("Subscribed to all events (wildcard)")

    async def unsubscribe_all(self, handler: Callable[[Event], Any]) -> None:
        """
        Remove handler from all subscriptions.
        Args:
            handler: Handler to remove
        """
        async with self._lock:
            # Remove from specific subscriptions
            for event_type in list(self._subscribers.keys()):
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)

            # Remove from wildcard
            if handler in self._wildcard_subscribers:
                self._wildcard_subscribers.remove(handler)

            logger.debug("Unsubscribed from all events")

    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        """
        Get recent event history.
        Args:
            event_type: Filter by event type (None for all)
            limit: Maximum number of events to return
        Returns:
            List of events, newest first
        """
        async def _get():
            async with self._lock:
                if event_type:
                    filtered = [e for e in self._history if e.type == event_type]
                else:
                    filtered = list(self._history)

                return list(reversed(filtered))[:limit]

        # Synchronous access to lock-protected data
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_get())
        finally:
            loop.close()

    def clear_history(self) -> None:
        """Clear event history."""
        async def _clear():
            async with self._lock:
                self._history.clear()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_clear())
        finally:
            loop.close()

    async def _safe_call_async(self, handler: Callable, event: Event) -> None:
        """Safely call async handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Error in async event handler for {event.type}: {e}", exc_info=True)

    async def _safe_call_sync(self, handler: Callable, event: Event) -> None:
        """Safely call sync handler by running in thread pool."""
        try:
            await asyncio.to_thread(handler, event)
        except Exception as e:
            logger.error(f"Error in sync event handler for {event.type}: {e}", exc_info=True)

    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, [])) + len(self._wildcard_subscribers)

    def list_event_types(self) -> list[str]:
        """List all event types that have subscribers."""
        event_types = list(self._subscribers.keys())
        if self._wildcard_subscribers:
            event_types.append("*")
        return sorted(event_types)
