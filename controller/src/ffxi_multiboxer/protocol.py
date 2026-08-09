from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from typing import Iterable

PROTOCOL_VERSION = 1


class MessageType(StrEnum):
    HELLO = "HELLO"
    HEARTBEAT = "HEARTBEAT"
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


def heartbeat(character: str, zone: str = "") -> Message:
    return Message(MessageType.HEARTBEAT, (character, zone))


def state_message(
    character: str,
    *,
    zone: str,
    hp_percent: int,
    mp_percent: int,
    tp: int,
    target_id: int,
    engaged: bool,
    casting: bool,
    x: float,
    y: float,
    z: float,
    heading: float,
    buffs: Iterable[int] = (),
) -> Message:
    return Message(
        MessageType.STATE,
        (
            character,
            zone,
            str(int(hp_percent)),
            str(int(mp_percent)),
            str(int(tp)),
            str(int(target_id)),
            "1" if engaged else "0",
            "1" if casting else "0",
            f"{float(x):.3f}",
            f"{float(y):.3f}",
            f"{float(z):.3f}",
            f"{float(heading):.5f}",
            ",".join(str(int(buff)) for buff in buffs),
        ),
    )


def command(command_id: str, scope: Scope, recipient: str, action: str, args: Iterable[str]) -> Message:
    return Message(MessageType.CMD, (command_id, scope.value, recipient, action, *tuple(args)))


def ack(command_id: str, character: str, status: str, detail: str = "") -> Message:
    return Message(MessageType.ACK, (command_id, character, status, detail))


def event(character: str, event_name: str, *fields: str) -> Message:
    return Message(MessageType.EVENT, (character, event_name, *fields))


def parse_state(msg: Message) -> dict[str, object]:
    if msg.kind != MessageType.STATE or len(msg.fields) < 13:
        raise ValueError("not a complete STATE message")
    buffs = frozenset(int(v) for v in msg.fields[12].split(",") if v)
    return {
        "character": msg.fields[0],
        "zone": msg.fields[1],
        "hp_percent": int(msg.fields[2]),
        "mp_percent": int(msg.fields[3]),
        "tp": int(msg.fields[4]),
        "target_id": int(msg.fields[5]),
        "engaged": msg.fields[6] == "1",
        "casting": msg.fields[7] == "1",
        "x": float(msg.fields[8]),
        "y": float(msg.fields[9]),
        "z": float(msg.fields[10]),
        "heading": float(msg.fields[11]),
        "buffs": buffs,
    }


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
