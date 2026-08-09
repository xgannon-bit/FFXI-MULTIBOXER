from __future__ import annotations

from .encounter import EncounterSession
from .intents import Intent, IntentArbiter, IntentKind
from .state import CharacterState
from .support import SupportPlanner
from .travel_session import TravelSession


def demo_support() -> None:
    encounter = EncounterSession()
    encounter.arm("simulation")
    encounter.activate(9001)

    gannon = CharacterState("Gannon", hp_percent=28, mp_percent=45, tp=1180, target_id=9001, engaged=True)
    coughdrop = CharacterState("Coughdrop", hp_percent=91, mp_percent=76, tp=420, target_id=9001)
    friend = CharacterState("FriendDRG", hp_percent=58, mp_percent=0, tp=1440, target_id=9001, engaged=True)

    planner = SupportPlanner()
    arbiter = IntentArbiter()
    candidates = planner.cure_intents(coughdrop, [gannon, friend, coughdrop])
    candidates.extend(
        [
            Intent("Coughdrop", IntentKind.STUN, "Stun", target_id=9001, score=9500, detail="simulated dangerous mob cast"),
            Intent("Gannon", IntentKind.WEAPONSKILL, "Swift Blade", target_id=9001, score=1200),
        ]
    )

    print("XI Command offline simulation")
    print(f"Encounter: {encounter.status} target={encounter.target_id}")
    print("Candidates:")
    for intent in arbiter.rank(candidates):
        print(f"  {intent.score:6.0f} {intent.actor:12} {intent.kind:12} {intent.action:14} -> {intent.target or intent.target_id}")

    winner = arbiter.choose(candidates)
    if winner:
        print(f"WINNER: {winner.actor} {winner.action} -> {winner.target or winner.target_id}")


def demo_travel() -> None:
    session = TravelSession.create("SIM-TRAVEL-1", "hp", "Ru'Lude Gardens", ["Gannon", "Coughdrop"])
    session.bind_command("Coughdrop", "T00000001")
    session.acknowledge("Coughdrop", True, "menu accepted")
    session.arrived("Coughdrop", "zone changed")
    session.bind_command("Gannon", "T00000002")
    session.acknowledge("Gannon", True, "menu accepted")
    session.arrived("Gannon", "zone changed")
    print("Travel:", session.summary(), "complete=", session.complete)


def main() -> None:
    demo_support()
    print()
    demo_travel()


if __name__ == "__main__":
    main()
