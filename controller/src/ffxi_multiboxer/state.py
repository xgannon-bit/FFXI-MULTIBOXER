from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass(slots=True)
class Position:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    heading: float = 0.0


@dataclass(slots=True)
class CharacterState:
    character: str
    zone: str = ""
    hp_percent: int = 100
    mp_percent: int = 100
    tp: int = 0
    target_id: int = 0
    engaged: bool = False
    casting: bool = False
    position: Position = field(default_factory=Position)
    buffs: frozenset[int] = field(default_factory=frozenset)
    updated_at: float = field(default_factory=monotonic)

    def touch(self) -> None:
        self.updated_at = monotonic()

    @property
    def alive(self) -> bool:
        return self.hp_percent > 0

    @property
    def combat_ready(self) -> bool:
        return self.alive and not self.casting

    def distance_to(self, other: "CharacterState") -> float:
        dx = self.position.x - other.position.x
        dy = self.position.y - other.position.y
        dz = self.position.z - other.position.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5
