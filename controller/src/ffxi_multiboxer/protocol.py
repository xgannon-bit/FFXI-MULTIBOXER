from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Iterable

PROTOCOL_VERSION = 1


class MessageType(StrEnum):
    HELLO = "HELLO"
    STATE = "STATE"
    CMD = "CMD"
    ACK = "ACK"
    EVENT = "EVENT"


class Scope(StrEnum):
    ALL = "ALL"
    PARTY = "PARTY"
    CHARACTER = "CHAR"


@dataclass(slots=True)
class Message:
    kind: MessageType
    fields: tuple[str, ...]

    def encode(self) -> bytes:
        clean = [str(PROTOCOL_VERSION), self.kind.value]
        clean.extend(_escape(v) for v in self.fields)
        return ("|".join(clean) + "\n").encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> "Message":
        line = data.decode("utf-8", errors="strict").strip()
        parts = _split_escaped(line)
        if len(parts) < 2:
            raise ValueError("short protocol message")
        version = int(parts[0])
        if version != PROTOCOL_VERSION:
            raise ValueError(f"unsupported protocol version: {version}")
        return cls(MessageType(parts[1]), tuple(parts[2:]))


def hello(character: str, addon_version: str, zone: str = "") -> Message:
    return Message(MessageType.HELLO, (character, addon_version, zone))


def command(command_id: str, scope: Scope, recipient: str, action: str, args: Iterable[str]) -> Message:
    return Message(MessageType.CMD, (command_id, scope.value, recipient, action, *tuple(args)))


def ack(command_id: str, character: str, status: str, detail: str = "") -> Message:
    return Message(MessageType.ACK, (command_id, character, status, detail))


def now_ms() -> int:
    return int(monotonic() * 1000)


def _escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\p").replace("\n", "\\n")


def _split_escaped(line: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    escaped = False
    for ch in line:
        if escaped:
            if ch == "p":
                buf.append("|")
            elif ch == "n":
                buf.append("\n")
            else:
                buf.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            out.append("".join(buf))
            buf.clear()
        else:
            buf.append(ch)
    if escaped:
        buf.append("\\")
    out.append("".join(buf))
    return out
