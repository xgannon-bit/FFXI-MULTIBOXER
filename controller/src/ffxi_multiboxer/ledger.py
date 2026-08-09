from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic


class CommandStatus(StrEnum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    ACKED = "ACKED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class CommandRecord:
    command_id: str
    character: str
    action: str
    status: CommandStatus = CommandStatus.QUEUED
    created_at: float = field(default_factory=monotonic)
    sent_at: float = 0.0
    finished_at: float = 0.0
    detail: str = ""


class CommandLedger:
    def __init__(self) -> None:
        self._records: dict[str, CommandRecord] = {}

    def create(self, command_id: str, character: str, action: str) -> CommandRecord:
        if command_id in self._records:
            raise ValueError(f"duplicate command id: {command_id}")
        record = CommandRecord(command_id, character, action)
        self._records[command_id] = record
        return record

    def sent(self, command_id: str) -> None:
        record = self._records[command_id]
        record.status = CommandStatus.SENT
        record.sent_at = monotonic()

    def finish(self, command_id: str, status: str, detail: str = "") -> None:
        record = self._records[command_id]
        normalized = status.strip().upper()
        record.status = CommandStatus.ACKED if normalized in {"OK", "ACK", "ACKED", "COMPLETE", "COMPLETED"} else CommandStatus.FAILED
        record.finished_at = monotonic()
        record.detail = detail

    def expire(self, timeout_seconds: float, now: float | None = None) -> list[CommandRecord]:
        now = monotonic() if now is None else now
        expired: list[CommandRecord] = []
        for record in self._records.values():
            if record.status != CommandStatus.SENT:
                continue
            basis = record.sent_at or record.created_at
            if now - basis >= timeout_seconds:
                record.status = CommandStatus.TIMED_OUT
                record.finished_at = now
                expired.append(record)
        return expired

    def cancel_open(self, *, action: str | None = None) -> list[CommandRecord]:
        cancelled: list[CommandRecord] = []
        for record in self._records.values():
            if record.status not in {CommandStatus.QUEUED, CommandStatus.SENT}:
                continue
            if action is not None and record.action.casefold() != action.casefold():
                continue
            record.status = CommandStatus.CANCELLED
            record.finished_at = monotonic()
            cancelled.append(record)
        return cancelled

    def get(self, command_id: str) -> CommandRecord | None:
        return self._records.get(command_id)

    def open(self) -> tuple[CommandRecord, ...]:
        return tuple(r for r in self._records.values() if r.status in {CommandStatus.QUEUED, CommandStatus.SENT})

    def snapshot(self) -> tuple[CommandRecord, ...]:
        return tuple(self._records.values())
