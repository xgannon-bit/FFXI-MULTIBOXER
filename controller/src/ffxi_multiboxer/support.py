from __future__ import annotations

from dataclasses import dataclass

from .intents import Intent, IntentKind
from .state import CharacterState


@dataclass(slots=True, frozen=True)
class CurePolicy:
    emergency_hp: int = 30
    high_hp: int = 50
    normal_hp: int = 70
    min_mp: int = 8

    def validate(self) -> None:
        if not (0 < self.emergency_hp < self.high_hp < self.normal_hp <= 100):
            raise ValueError("HP thresholds must increase and be within 1..100")
        if not 0 <= self.min_mp <= 100:
            raise ValueError("min_mp must be within 0..100")


class SupportPlanner:
    """Produces support intents; the central arbiter decides which actor wins.

    This module deliberately does not know Ashita command syntax or server packet
    details. It turns party state into ranked intent candidates only.
    """

    def __init__(self, policy: CurePolicy | None = None) -> None:
        self.policy = policy or CurePolicy()
        self.policy.validate()

    def cure_intents(self, healer: CharacterState, party: list[CharacterState]) -> list[Intent]:
        if not healer.alive or healer.casting or healer.mp_percent < self.policy.min_mp:
            return []
        out: list[Intent] = []
        for member in party:
            if not member.alive or member.hp_percent >= self.policy.normal_hp:
                continue
            deficit = 100 - member.hp_percent
            if member.hp_percent <= self.policy.emergency_hp:
                spell = "Cure IV"
                tier_bonus = 400
            elif member.hp_percent <= self.policy.high_hp:
                spell = "Cure III"
                tier_bonus = 200
            else:
                spell = "Cure II"
                tier_bonus = 50
            # Large deficits dominate, while the emergency band produces an
            # explicit jump. Deterministic tie-breaking is handled by arbiter.
            score = float(deficit * 10 + tier_bonus)
            out.append(
                Intent(
                    actor=healer.character,
                    kind=IntentKind.CURE,
                    action=spell,
                    target=member.character,
                    score=score,
                    resource_key=f"heal:{member.character.casefold()}",
                    detail=f"hp={member.hp_percent}% mp={healer.mp_percent}%",
                )
            )
        return out

    def emergency_self_preservation(self, actor: CharacterState) -> Intent | None:
        if not actor.alive or actor.hp_percent > self.policy.emergency_hp:
            return None
        return Intent(
            actor=actor.character,
            kind=IntentKind.CURE,
            action="Cure IV",
            target=actor.character,
            score=5000 + (100 - actor.hp_percent) * 10,
            resource_key=f"heal:{actor.character.casefold()}",
            detail="emergency self-preservation",
        )
