from __future__ import annotations

from dataclasses import asdict, dataclass, field
from json import dumps
from pathlib import Path
from time import time
from typing import Any


@dataclass(slots=True)
class TelemetryEvent:
    event: str
    character: str = ""
    command_id: str = ""
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time)


class TelemetryLog:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.events: list[TelemetryEvent] = []

    def emit(self, event: TelemetryEvent) -> None:
        self.events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(dumps(asdict(event), sort_keys=True) + "\n")

    def record(self, event: str, *, character: str = "", command_id: str = "", detail: str = "", **data: Any) -> None:
        self.emit(TelemetryEvent(event, character, command_id, detail, data))

    def recent(self, limit: int = 50) -> tuple[TelemetryEvent, ...]:
        if limit <= 0:
            return ()
        return tuple(self.events[-limit:])
