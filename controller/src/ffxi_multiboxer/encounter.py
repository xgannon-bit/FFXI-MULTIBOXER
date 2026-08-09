from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic


class EncounterStatus(StrEnum):
    DISARMED = "DISARMED"
    ARMED = "ARMED"
    ACTIVE = "ACTIVE"


@dataclass(slots=True)
class EncounterSession:
    status: EncounterStatus = EncounterStatus.DISARMED
    target_id: int = 0
    armed_at: float = 0.0
    active_at: float = 0.0
    reason: str = ""

    def arm(self, reason: str = "manual") -> None:
        self.status = EncounterStatus.ARMED
        self.target_id = 0
        self.armed_at = monotonic()
        self.active_at = 0.0
        self.reason = reason

    def activate(self, target_id: int) -> None:
        if self.status != EncounterStatus.ARMED:
            raise RuntimeError("encounter must be manually armed before activation")
        if target_id <= 0:
            raise ValueError("target_id must be positive")
        self.status = EncounterStatus.ACTIVE
        self.target_id = target_id
        self.active_at = monotonic()

    def disarm(self, reason: str = "manual") -> None:
        self.status = EncounterStatus.DISARMED
        self.target_id = 0
        self.reason = reason

    def permits_combat_action(self, target_id: int | None = None) -> bool:
        if self.status != EncounterStatus.ACTIVE:
            return False
        if target_id is not None and target_id > 0 and target_id != self.target_id:
            return False
        return True
