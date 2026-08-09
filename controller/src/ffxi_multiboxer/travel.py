from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import count
from time import monotonic

from .protocol import Scope, command


class TravelSystem(StrEnum):
    HOME_POINT = "hp"
    WAYPOINT = "wp"
    PROTO_WAYPOINT = "pwp"
    SURVIVAL_GUIDE = "sg"
    ESCHA = "ew"
    UNITY = "un"
    ABYSSEA = "ab"
    RUNIC_PORTAL = "po"
    VOIDWATCH = "vw"
    SORTIE = "so"
    ODYSSEY = "od"
    LIMBUS = "li"


@dataclass(slots=True, frozen=True)
class TravelRequest:
    system: TravelSystem
    destination: str
    sub_destination: str = ""
    scope: Scope = Scope.ALL
    recipient: str = "*"

    def args(self) -> tuple[str, ...]:
        return (self.system.value, self.destination, self.sub_destination)


@dataclass(slots=True)
class Dispatch:
    due_at: float
    address: tuple[str, int]
    payload: bytes
    command_id: str
    character: str


class TravelCoordinator:
    """Creates staggered per-client travel commands.

    FFXI menu interactions are sensitive to multiple actions landing at the exact
    same time. Superwarp uses delayed local IPC for the same reason. XI Command
    centralizes that behavior so every travel provider gets consistent ordering,
    acknowledgement and cancellation semantics.
    """

    def __init__(self, stagger_seconds: float = 0.30) -> None:
        if not 0 <= stagger_seconds <= 5:
            raise ValueError("stagger_seconds must be between 0 and 5")
        self.stagger_seconds = stagger_seconds
        self._ids = count(1)

    def build_dispatches(
        self,
        request: TravelRequest,
        clients: list[tuple[str, tuple[str, int]]],
        *,
        leader: str | None = None,
    ) -> list[Dispatch]:
        ordered = sorted(clients, key=lambda item: item[0].casefold())
        # Default to leader-last so the controlling client remains available
        # while the other boxes begin their menu interaction.
        if leader:
            ordered.sort(key=lambda item: item[0].casefold() == leader.casefold())

        start = monotonic()
        out: list[Dispatch] = []
        for index, (character, address) in enumerate(ordered):
            command_id = f"T{next(self._ids):08d}"
            msg = command(
                command_id,
                Scope.CHARACTER,
                character,
                "TRAVEL",
                request.args(),
            )
            out.append(
                Dispatch(
                    due_at=start + (index * self.stagger_seconds),
                    address=address,
                    payload=msg.encode(),
                    command_id=command_id,
                    character=character,
                )
            )
        return out
