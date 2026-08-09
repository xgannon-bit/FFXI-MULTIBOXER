from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic

from .protocol import Message, MessageType, Scope
from .travel import TravelCoordinator, TravelRequest, TravelSystem

HOST = "127.0.0.1"
PORT = 19775


@dataclass(slots=True)
class Client:
    character: str
    address: tuple[str, int]
    addon_version: str = ""
    zone: str = ""
    last_seen: float = field(default_factory=monotonic)


class Controller(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self.clients: dict[str, Client] = {}
        self.travel = TravelCoordinator(stagger_seconds=0.30)
        self.pending: dict[str, str] = {}
        self.leader: str | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        print(f"XI Command controller listening on udp://{HOST}:{PORT}")

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            msg = Message.decode(data)
        except Exception as exc:
            print(f"bad packet from {addr}: {exc}")
            return

        if msg.kind == MessageType.HELLO and len(msg.fields) >= 2:
            character = msg.fields[0]
            addon_version = msg.fields[1]
            zone = msg.fields[2] if len(msg.fields) >= 3 else ""
            self.clients[character.casefold()] = Client(character, addr, addon_version, zone)
            if self.leader is None:
                self.leader = character
            print(f"agent online: {character} {addr} zone={zone or '?'}")
            return

        if msg.kind == MessageType.STATE and msg.fields:
            key = msg.fields[0].casefold()
            if key in self.clients:
                self.clients[key].last_seen = monotonic()
            return

        if msg.kind == MessageType.ACK and len(msg.fields) >= 3:
            command_id, character, status = msg.fields[:3]
            detail = msg.fields[3] if len(msg.fields) >= 4 else ""
            self.pending.pop(command_id, None)
            print(f"ACK {command_id} {character}: {status} {detail}")
            return

        if msg.kind == MessageType.EVENT:
            print("EVENT", *msg.fields)

    async def issue_travel(self, request: TravelRequest) -> None:
        active = [(c.character, c.address) for c in self.clients.values() if monotonic() - c.last_seen < 10]
        if request.scope == Scope.CHARACTER:
            active = [(name, addr) for name, addr in active if name.casefold() == request.recipient.casefold()]
        if not active:
            print("No active agents match the requested scope.")
            return
        assert self.transport is not None
        dispatches = self.travel.build_dispatches(request, active, leader=self.leader)
        for item in dispatches:
            delay = max(0.0, item.due_at - monotonic())
            await asyncio.sleep(delay)
            self.pending[item.command_id] = item.character
            self.transport.sendto(item.payload, item.address)
            print(f"SEND {item.command_id} -> {item.character}: {request.system} {request.destination} {request.sub_destination}")


async def console(controller: Controller) -> None:
    loop = asyncio.get_running_loop()
    print('Commands: clients | leader <name> | travel <all|char:name> <system> <destination> [sub] | quit')
    while True:
        raw = await loop.run_in_executor(None, input, "xmb> ")
        parts = raw.strip().split()
        if not parts:
            continue
        cmd = parts[0].casefold()
        if cmd in {"quit", "exit"}:
            return
        if cmd == "clients":
            for c in controller.clients.values():
                age = monotonic() - c.last_seen
                print(f"{c.character:16} {c.address[0]}:{c.address[1]} age={age:.1f}s zone={c.zone}")
            continue
        if cmd == "leader" and len(parts) >= 2:
            controller.leader = parts[1]
            print(f"leader={controller.leader}")
            continue
        if cmd == "travel" and len(parts) >= 4:
            scope_token = parts[1]
            system = TravelSystem(parts[2].casefold())
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
