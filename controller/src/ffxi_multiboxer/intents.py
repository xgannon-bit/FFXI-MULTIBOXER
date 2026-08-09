from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic


class IntentKind(StrEnum):
    CURE = "CURE"
    STATUS_CURE = "STATUS_CURE"
    BUFF = "BUFF"
    DEBUFF = "DEBUFF"
    DISPEL = "DISPEL"
    STUN = "STUN"
    WEAPONSKILL = "WEAPONSKILL"
    MAGIC_BURST = "MAGIC_BURST"
    MOVE = "MOVE"
    TRAVEL = "TRAVEL"


@dataclass(slots=True, frozen=True)
class Intent:
    actor: str
    kind: IntentKind
    action: str
    target: str = ""
    target_id: int = 0
    score: float = 0.0
    resource_key: str = ""
    created_at: float = field(default_factory=monotonic)
    detail: str = ""

    def reservation_key(self) -> str:
        if self.resource_key:
            return self.resource_key
        if self.kind in {IntentKind.CURE, IntentKind.STATUS_CURE, IntentKind.BUFF}:
            return f"{self.kind}:{self.target.casefold()}:{self.action.casefold()}"
        if self.kind in {IntentKind.STUN, IntentKind.DISPEL}:
            return f"{self.kind}:{self.target_id}"
        return f"{self.actor.casefold()}:{self.kind}:{self.action.casefold()}"


@dataclass(slots=True)
class Reservation:
    key: str
    owner: str
    expires_at: float
    intent: Intent


class ReservationBook:
    def __init__(self) -> None:
        self._items: dict[str, Reservation] = {}

    def _purge(self, now: float | None = None) -> None:
        now = monotonic() if now is None else now
        expired = [key for key, item in self._items.items() if item.expires_at <= now]
        for key in expired:
            self._items.pop(key, None)

    def available(self, intent: Intent, now: float | None = None) -> bool:
        self._purge(now)
        current = self._items.get(intent.reservation_key())
        return current is None or current.owner.casefold() == intent.actor.casefold()

    def reserve(self, intent: Intent, ttl_seconds: float = 2.5, now: float | None = None) -> Reservation:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        now = monotonic() if now is None else now
        self._purge(now)
        key = intent.reservation_key()
        current = self._items.get(key)
        if current is not None and current.owner.casefold() != intent.actor.casefold():
            raise RuntimeError(f"resource already reserved by {current.owner}: {key}")
        reservation = Reservation(key, intent.actor, now + ttl_seconds, intent)
        self._items[key] = reservation
        return reservation

    def release(self, key: str, owner: str | None = None) -> bool:
        item = self._items.get(key)
        if item is None:
            return False
        if owner is not None and item.owner.casefold() != owner.casefold():
            return False
        self._items.pop(key, None)
        return True

    def snapshot(self) -> tuple[Reservation, ...]:
        self._purge()
        return tuple(self._items.values())


class IntentArbiter:
    """Selects a deterministic winner from competing party intents."""

    def __init__(self, reservations: ReservationBook | None = None) -> None:
        self.reservations = reservations or ReservationBook()

    def rank(self, intents: list[Intent]) -> list[Intent]:
        eligible = [intent for intent in intents if self.reservations.available(intent)]
        return sorted(
            eligible,
            key=lambda x: (-x.score, x.created_at, x.actor.casefold(), x.action.casefold()),
        )

    def choose(self, intents: list[Intent], *, reserve: bool = True, ttl_seconds: float = 2.5) -> Intent | None:
        ranked = self.rank(intents)
        if not ranked:
            return None
        winner = ranked[0]
        if reserve:
            self.reservations.reserve(winner, ttl_seconds=ttl_seconds)
        return winner
