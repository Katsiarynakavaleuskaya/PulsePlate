"""Domain event adapter for adherence model.

RU: Адаптер доменных событий для модели adherence.
EN: Adapter layer mapping domain events to adherence model events.

This layer enables future extensibility by decoupling domain-specific
events from the core Beta-Binomial model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .adherence_model import AdherenceEventType

DomainEventName = Literal[
    "meal_logged",
    "slip",
    # Future extensibility:
    "day_completed",
    "workout_logged",
]


@dataclass(frozen=True)
class DomainEvent:
    """Unified domain event representation.

    RU: Унифицированное доменное событие.
    EN: Normalized domain event.
    """

    name: DomainEventName
    weight: float = 1.0


def to_adherence_event(event: DomainEvent) -> tuple[AdherenceEventType, float]:
    """Map domain event to micro-model event.

    RU: Преобразование доменного события в событие микромодели.
    EN: Map domain event to micro-model event.

    Args:
        event: Domain event to map

    Returns:
        Tuple of (adherence_event_type, weight)

    Raises:
        ValueError: If event type is not supported
    """
    if event.name in ("meal_logged", "day_completed", "workout_logged"):
        return "meal_logged", event.weight
    if event.name == "slip":
        return "slip", event.weight

    # Defensive, should not happen due to typing
    raise ValueError(f"Unsupported domain event: {event.name}")
