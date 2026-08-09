# FFXI-MULTIBOXER / XI Command

Experimental **attended** multibox orchestration for Final Fantasy XI, initially targeting CatsEyeXI + Ashita v4.

## Goals

- One controller coordinates multiple local FFXI clients.
- Fast state/command transport over localhost UDP.
- Central intent arbitration so boxes do not double-cure, double-stun, waste WS, etc.
- Formation/positioning, support AI, skillchains, magic bursts and reactive interrupts.
- Superwarp-style synchronized travel for all local characters.
- Developer telemetry and replayable decision logs.

## Hard boundaries

This project is designed for an attended test environment. The normal build deliberately does **not** include autonomous claiming, pulling, AFK farming or AFK leveling loops. An encounter must be manually armed and activated before the controller permits combat actions.

## Repository layout

```text
ashita/addons/xicommand/   Ashita v4 in-game agent
controller/                Python central coordinator
  src/ffxi_multiboxer/
docs/                      protocol, travel and roadmap docs
```

## Current state

### M0 - bootstrap: complete

- Versioned wire protocol
- controller skeleton
- Ashita command parser
- travel request model
- leader-last staggered dispatch

### M1 - core orchestration: implemented on `phase1-core`

- character state model
- online/offline registry behavior
- attended encounter state machine
- central intent arbitration
- action/resource reservations
- command ACK/timeout ledger
- structured JSONL telemetry
- travel session progress tracking
- support/cure intent prototype
- offline simulation harness
- Python unit tests and GitHub Actions CI

### M2 - Ashita transport: started

The Ashita agent now has a non-blocking localhost UDP transport using LuaSocket, HELLO/heartbeat messages, controller command receiving, ACK replies, reconnect/ping diagnostics and a live TRAVEL command bridge. Travel execution is intentionally still a dry-run provider until CatsEye-specific Home Point menu behavior is implemented.

See `docs/ROADMAP.md` for all milestones.

## Development setup

Controller requires Python 3.12+.

```powershell
cd controller
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m unittest discover -s tests -v
xmb-sim
xmb-controller
```

Ashita addon installation:

```text
<Ashita>\addons\xicommand\
```

then in game:

```text
/addon load xicommand
/xmb status
/xmb ping
```

Controller console examples:

```text
clients
state
leader Gannon
travel all hp "Ru'Lude Gardens" 1
travel char:Coughdrop sg "Valkurm Dunes"
arm
activate 0x12345678
disarm
pending
```

In-game local diagnostics:

```text
/xmb status
/xmb reconnect
/xmb ping
/xmb travel hp "Ru'Lude Gardens" 1
/xmb cancel
```

## Superwarp inspiration

AkadenTK/superwarp is BSD-3-Clause licensed and valuable prior art for FFXI travel systems. It supports Home Points, Waypoints, Proto-Waypoints, Survival Guides and many additional retail systems, including multibox IPC. XI Command uses a provider interface so CatsEye-specific destinations and menu flows can be supported without importing retail-only assumptions.

See `docs/TRAVEL.md` for the travel design and porting plan.
