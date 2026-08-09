from __future__ import annotations

import unittest

from ffxi_multiboxer.encounter import EncounterSession, EncounterStatus
from ffxi_multiboxer.intents import Intent, IntentArbiter, IntentKind, ReservationBook
from ffxi_multiboxer.ledger import CommandLedger, CommandStatus
from ffxi_multiboxer.protocol import Message, Scope, state_message, parse_state
from ffxi_multiboxer.travel import TravelCoordinator, TravelRequest, TravelSystem


class ProtocolTests(unittest.TestCase):
    def test_escape_roundtrip(self) -> None:
        original = Message.decode(b"1|EVENT|Gannon|NOTE|a\\pb\\nline\\\\tail\n")
        encoded = original.encode()
        decoded = Message.decode(encoded)
        self.assertEqual(decoded, original)

    def test_state_roundtrip(self) -> None:
        msg = state_message(
            "Gannon",
            zone="Ru'Lude Gardens",
            hp_percent=87,
            mp_percent=42,
            tp=1234,
            target_id=1001,
            engaged=True,
            casting=False,
            x=1.25,
            y=-3.5,
            z=0.75,
            heading=1.2,
            buffs=(33, 580),
        )
        decoded = Message.decode(msg.encode())
        state = parse_state(decoded)
        self.assertEqual(state["character"], "Gannon")
        self.assertEqual(state["tp"], 1234)
        self.assertEqual(state["buffs"], frozenset({33, 580}))
        self.assertTrue(state["engaged"])


class EncounterTests(unittest.TestCase):
    def test_manual_gate(self) -> None:
        encounter = EncounterSession()
        self.assertFalse(encounter.permits_combat_action())
        encounter.arm()
        self.assertEqual(encounter.status, EncounterStatus.ARMED)
        self.assertFalse(encounter.permits_combat_action())
        encounter.activate(123)
        self.assertTrue(encounter.permits_combat_action(123))
        self.assertFalse(encounter.permits_combat_action(124))
        encounter.disarm()
        self.assertFalse(encounter.permits_combat_action(123))

    def test_cannot_activate_without_arm(self) -> None:
        with self.assertRaises(RuntimeError):
            EncounterSession().activate(123)


class IntentTests(unittest.TestCase):
    def test_highest_score_wins(self) -> None:
        arbiter = IntentArbiter()
        winner = arbiter.choose([
            Intent("Rdm", IntentKind.CURE, "Cure III", target="Gannon", score=50),
            Intent("Whm", IntentKind.CURE, "Cure V", target="Gannon", score=90),
        ])
        self.assertIsNotNone(winner)
        self.assertEqual(winner.actor, "Whm")

    def test_reservation_prevents_duplicate(self) -> None:
        book = ReservationBook()
        arbiter = IntentArbiter(book)
        first = Intent("Rdm", IntentKind.STUN, "Stun", target_id=700, score=100)
        second = Intent("Blm", IntentKind.STUN, "Stun", target_id=700, score=90)
        self.assertEqual(arbiter.choose([first, second]).actor, "Rdm")
        self.assertIsNone(arbiter.choose([second]))
        self.assertTrue(book.release(first.reservation_key(), owner="Rdm"))
        self.assertEqual(arbiter.choose([second]).actor, "Blm")


class LedgerTests(unittest.TestCase):
    def test_ack_and_timeout(self) -> None:
        ledger = CommandLedger()
        rec = ledger.create("C1", "Gannon", "CAST")
        ledger.sent("C1")
        ledger.finish("C1", "OK", "done")
        self.assertEqual(rec.status, CommandStatus.ACKED)

        rec2 = ledger.create("C2", "Coughdrop", "TRAVEL")
        ledger.sent("C2")
        rec2.sent_at = 1.0
        expired = ledger.expire(5.0, now=10.0)
        self.assertEqual(expired[0].status, CommandStatus.TIMED_OUT)


class TravelTests(unittest.TestCase):
    def test_leader_is_dispatched_last(self) -> None:
        coordinator = TravelCoordinator(stagger_seconds=0.30)
        request = TravelRequest(TravelSystem.HOME_POINT, "Jeuno", scope=Scope.ALL)
        items = coordinator.build_dispatches(
            request,
            [
                ("Gannon", ("127.0.0.1", 1001)),
                ("Coughdrop", ("127.0.0.1", 1002)),
                ("Bardbox", ("127.0.0.1", 1003)),
            ],
            leader="Gannon",
        )
        self.assertEqual(items[-1].character, "Gannon")
        self.assertGreater(items[1].due_at, items[0].due_at)
        self.assertGreater(items[2].due_at, items[1].due_at)


if __name__ == "__main__":
    unittest.main()
