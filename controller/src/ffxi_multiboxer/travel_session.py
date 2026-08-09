from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic


class ParticipantStatus(StrEnum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    ACKED = "ACKED"
    ARRIVED = "ARRIVED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class TravelParticipant:
    character: str
    command_id: str = ""
    status: ParticipantStatus = ParticipantStatus.QUEUED
    detail: str = ""
    updated_at: float = field(default_factory=monotonic)

    def set(self, status: ParticipantStatus, detail: str = "") -> None:
        self.status = status
        self.detail = detail
        self.updated_at = monotonic()


@dataclass(slots=True)
class TravelSession:
    session_id: str
    system: str
    destination: str
    sub_destination: str = ""
    participants: dict[str, TravelParticipant] = field(default_factory=dict)
    created_at: float = field(default_factory=monotonic)
    cancelled: bool = False

    @classmethod
    def create(cls, session_id: str, system: str, destination: str, characters: list[str], sub_destination: str = "") -> "TravelSession":
        return cls(
            session_id=session_id,
            system=system,
            destination=destination,
            sub_destination=sub_destination,
            participants={name.casefold(): TravelParticipant(name) for name in characters},
        )

    def participant(self, character: str) -> TravelParticipant:
        return self.participants[character.casefold()]

    def bind_command(self, character: str, command_id: str) -> None:
        item = self.participant(character)
        item.command_id = command_id
        item.set(ParticipantStatus.SENT)

    def acknowledge(self, character: str, ok: bool, detail: str = "") -> None:
        self.participant(character).set(ParticipantStatus.ACKED if ok else ParticipantStatus.FAILED, detail)

    def arrived(self, character: str, detail: str = "") -> None:
        self.participant(character).set(ParticipantStatus.ARRIVED, detail)

    def skip(self, character: str, detail: str) -> None:
        self.participant(character).set(ParticipantStatus.SKIPPED, detail)

    def cancel(self) -> None:
        self.cancelled = True
        for item in self.participants.values():
            if item.status in {ParticipantStatus.QUEUED, ParticipantStatus.SENT}:
                item.set(ParticipantStatus.CANCELLED)

    @property
    def complete(self) -> bool:
        terminal = {ParticipantStatus.ARRIVED, ParticipantStatus.FAILED, ParticipantStatus.SKIPPED, ParticipantStatus.CANCELLED}
        return all(item.status in terminal for item in self.participants.values())

    def summary(self) -> dict[str, int]:
        counts = {status.value: 0 for status in ParticipantStatus}
        for item in self.participants.values():
            counts[item.status.value] += 1
        return counts
