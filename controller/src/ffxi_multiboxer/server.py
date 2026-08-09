from __future__ import annotations

import asyncio
import shlex
from dataclasses import dataclass, field
from time import monotonic

from .encounter import EncounterSession
from .ledger import CommandLedger
from .protocol import Message, MessageType, Scope, command, parse_state
from .state import CharacterState, Position
from .telemetry import TelemetryLog
from .travel import TravelCoordinator, TravelRequest, TravelSystem

HOST = "127.0.0.1"
PORT = 19775
ONLINE_TIMEOUT = 10.0
COMMAND_TIMEOUT = 8.0

COMBAT_ACTIONS = {
    "CAST",
    "JA",
    "WS",
    "STUN",
    "CURE",
    "DEBUFF",
    "DISPEL",
    "ENGAGE",
    "MOVE_COMBAT",
}


@dataclass(slots=True)
class Client:
    character: str
    address: tuple[str, int]
    addon_version: str = ""
    zone: str = ""
    last_seen: float = field(default_factory=monotonic)
    state: CharacterState | None = None

    @property
    def online(self) -> bool:
        return monotonic() - self.last_seen < ONLINE_TIMEOUT


class Controller(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.clients: dict[str, Client] = {}
        self.travel = TravelCoordinator(stagger_seconds=0.30)
        self.ledger = CommandLedger()
        self.encounter = EncounterSession()
        self.telemetry = TelemetryLog("logs/xicommand.jsonl")
        self.leader: str | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        print(f"XI Command controller listening on udp://{HOST}:{PORT}")

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            msg = Message.decode(data)
        except Exception as exc:
            print(f"bad packet from {addr}: {exc}")
            self.telemetry.record("bad_packet", detail=str(exc), address=str(addr))
            return

        if msg.kind == MessageType.HELLO and len(msg.fields) >= 2:
            self._on_hello(msg, addr)
            return

        if msg.kind == MessageType.HEARTBEAT and msg.fields:
            self._touch_client(msg.fields[0], addr, zone=msg.fields[1] if len(msg.fields) > 1 else "")
            return

        if msg.kind == MessageType.STATE:
            self._on_state(msg, addr)
            return

        if msg.kind == MessageType.ACK and len(msg.fields) >= 3:
            command_id, character, status = msg.fields[:3]
            detail = msg.fields[3] if len(msg.fields) >= 4 else ""
            try:
                self.ledger.finish(command_id, status, detail)
            except KeyError:
                self.telemetry.record("orphan_ack", character=character, command_id=command_id, detail=detail)
            else:
                self.telemetry.record("ack", character=character, command_id=command_id, detail=detail, status=status)
            print(f"ACK {command_id} {character}: {status} {detail}")
            return

        if msg.kind == MessageType.EVENT:
            character = msg.fields[0] if msg.fields else ""
            event_name = msg.fields[1] if len(msg.fields) > 1 else "EVENT"
            rest = list(msg.fields[2:])
            self.telemetry.record(event_name, character=character, fields=rest)
            print("EVENT", *msg.fields)

    def _on_hello(self, msg: Message, addr: tuple[str, int]) -> None:
        character = msg.fields[0]
        addon_version = msg.fields[1]
        zone = msg.fields[2] if len(msg.fields) >= 3 else ""
        key = character.casefold()
        existing = self.clients.get(key)
        if existing is None:
            self.clients[key] = Client(character, addr, addon_version, zone)
        else:
            existing.address = addr
            existing.addon_version = addon_version
            existing.zone = zone
            existing.last_seen = monotonic()
        if self.leader is None:
            self.leader = character
        self.telemetry.record("agent_online", character=character, zone=zone, address=str(addr), addon_version=addon_version)
        print(f"agent online: {character} {addr} zone={zone or '?'}")

    def _touch_client(self, character: str, addr: tuple[str, int], *, zone: str = "") -> Client:
        key = character.casefold()
        client = self.clients.get(key)
        if client is None:
            client = Client(character, addr, zone=zone)
            self.clients[key] = client
        client.address = addr
        client.last_seen = monotonic()
        if zone:
            client.zone = zone
        return client

    def _on_state(self, msg: Message, addr: tuple[str, int]) -> None:
        try:
            raw = parse_state(msg)
        except Exception as exc:
            self.telemetry.record("bad_state", detail=str(exc))
            return
        character = str(raw["character"])
        client = self._touch_client(character, addr, zone=str(raw["zone"]))
        client.state = CharacterState(
            character=character,
            zone=str(raw["zone"]),
            hp_percent=int(raw["hp_percent"]),
            mp_percent=int(raw["mp_percent"]),
            tp=int(raw["tp"]),
            target_id=int(raw["target_id"]),
            engaged=bool(raw["engaged"]),
            casting=bool(raw["casting"]),
            position=Position(float(raw["x"]), float(raw["y"]), float(raw["z"]), float(raw["heading"])),
            buffs=frozenset(raw["buffs"]),  # type: ignore[arg-type]
        )

    def active_clients(self, scope: Scope = Scope.ALL, recipient: str = "*") -> list[Client]:
        active = [client for client in self.clients.values() if client.online]
        if scope == Scope.CHARACTER:
            active = [client for client in active if client.character.casefold() == recipient.casefold()]
        return sorted(active, key=lambda c: c.character.casefold())

    def command_allowed(self, action: str, target_id: int = 0) -> bool:
        if action.upper() not in COMBAT_ACTIONS:
            return True
        return self.encounter.permits_combat_action(target_id if target_id > 0 else None)

    def send_character_command(self, character: str, action: str, args: tuple[str, ...] = (), *, command_id: str, target_id: int = 0) -> bool:
        if not self.command_allowed(action, target_id):
            print(f"BLOCKED {action}: encounter is not active/authorized")
            self.telemetry.record("command_blocked", character=character, command_id=command_id, action=action, target_id=target_id)
            return False
        client = self.clients.get(character.casefold())
        if client is None or not client.online or self.transport is None:
            return False
        msg = command(command_id, Scope.CHARACTER, client.character, action, args)
        self.ledger.create(command_id, client.character, action)
        self.transport.sendto(msg.encode(), client.address)
        self.ledger.sent(command_id)
        self.telemetry.record("command_sent", character=client.character, command_id=command_id, action=action, args=list(args))
        return True

    async def issue_travel(self, request: TravelRequest) -> None:
        active = [(c.character, c.address) for c in self.active_clients(request.scope, request.recipient)]
        if not active:
            print("No active agents match the requested scope.")
            return
        assert self.transport is not None
        dispatches = self.travel.build_dispatches(request, active, leader=self.leader)
        self.telemetry.record("travel_session_start", system=request.system.value, destination=request.destination, participants=[name for name, _ in active])
        for item in dispatches:
            delay = max(0.0, item.due_at - monotonic())
            await asyncio.sleep(delay)
            self.ledger.create(item.command_id, item.character, "TRAVEL")
            self.transport.sendto(item.payload, item.address)
            self.ledger.sent(item.command_id)
            self.telemetry.record("travel_sent", character=item.character, command_id=item.command_id, system=request.system.value, destination=request.destination, sub=request.sub_destination)
            print(f"SEND {item.command_id} -> {item.character}: {request.system} {request.destination} {request.sub_destination}")

    def maintenance(self) -> None:
        for record in self.ledger.expire(COMMAND_TIMEOUT):
            print(f"TIMEOUT {record.command_id} -> {record.character}")
            self.telemetry.record("command_timeout", character=record.character, command_id=record.command_id, action=record.action)


async def console(controller: Controller) -> None:
    loop = asyncio.get_running_loop()
    print("Commands: clients | state | leader <name> | arm | activate <target_id> | disarm | travel <all|char:name> <system> <destination> [sub] | pending | quit")
    while True:
        controller.maintenance()
        raw = await loop.run_in_executor(None, input, "xmb> ")
        try:
            parts = shlex.split(raw.strip())
        except ValueError as exc:
            print(f"parse error: {exc}")
            continue
        if not parts:
            continue
        cmd = parts[0].casefold()
        if cmd in {"quit", "exit"}:
            return
        if cmd == "clients":
            for c in controller.clients.values():
                age = monotonic() - c.last_seen
                print(f"{c.character:16} {c.address[0]}:{c.address[1]} age={age:.1f}s online={c.online} zone={c.zone}")
            continue
        if cmd == "state":
            for c in controller.active_clients():
                s = c.state
                if s is None:
                    print(f"{c.character:16} no state yet")
                else:
                    print(f"{c.character:16} HP={s.hp_percent:3}% MP={s.mp_percent:3}% TP={s.tp:4} zone={s.zone} target={s.target_id} engaged={s.engaged}")
            continue
        if cmd == "leader" and len(parts) >= 2:
            controller.leader = parts[1]
            print(f"leader={controller.leader}")
            continue
        if cmd == "arm":
            controller.encounter.arm()
            print("Encounter ARMED; activate with an explicitly player-selected target id.")
            continue
        if cmd == "activate" and len(parts) >= 2:
            try:
                controller.encounter.activate(int(parts[1], 0))
            except (ValueError, RuntimeError) as exc:
                print(exc)
            else:
                print(f"Encounter ACTIVE target={controller.encounter.target_id}")
            continue
        if cmd == "disarm":
            controller.encounter.disarm()
            print("Encounter DISARMED")
            continue
        if cmd == "pending":
            for record in controller.ledger.open():
                print(f"{record.command_id} {record.character} {record.action} {record.status}")
            continue
        if cmd == "travel" and len(parts) >= 4:
            scope_token = parts[1]
            try:
                system = TravelSystem(parts[2].casefold())
            except ValueError:
                print("unknown travel system")
                continue
            destination = parts[3]
            sub = parts[4] if len(parts) >= 5 else ""
            if scope_token.casefold() == "all":
                scope, recipient = Scope.ALL, "*"
            elif scope_token.casefold().startswith("char:"):
                scope, recipient = Scope.CHARACTER, scope_token.split(":", 1)[1]
            else:
                print("scope must be all or char:<name>")
                continue
            await controller.issue_travel(TravelRequest(system, destination, sub, scope, recipient))
            continue
        print("Unknown command.")


async def run() -> None:
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(Controller, local_addr=(HOST, PORT))
    try:
        await console(protocol)  # type: ignore[arg-type]
    finally:
        transport.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
