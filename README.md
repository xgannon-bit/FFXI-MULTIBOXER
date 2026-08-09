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

This project is designed for an attended test environment. The normal build deliberately does **not** include autonomous claiming, pulling, AFK farming or AFK leveling loops. An encounter must be initiated/authorized by the player before combat orchestration is enabled.

## Repository layout

```text
ashita/addons/xicommand/   Ashita v4 in-game agent
controller/                Python central coordinator
  src/ffxi_multiboxer/
docs/                      protocol and subsystem design
```

## Current milestone: M0 + Travel foundation

Implemented first:

- UDP protocol and client registry
- acknowledgements and command IDs
- travel command model (`hp`, `wp`, `pwp`, `sg`, etc.)
- scopes: one character, party-local, all-local
- staggered dispatch for menu-heavy travel
- Ashita v4 command bridge skeleton (`/xmb ...`)
- explicit manual encounter gate

The travel subsystem is intentionally provider-based. We are reimplementing the useful ideas from Superwarp rather than coupling the whole application to Windower. The first provider will target CatsEye/Ashita menu behavior; a compatibility provider can later forward to existing server-approved travel addons.

## Development setup

Controller requires Python 3.12+.

```powershell
cd controller
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
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
```

## Initial commands

```text
/xmb status
/xmb arm              -- manually authorize current encounter
/xmb disarm
/xmb travel all hp "Ru'Lude Gardens" 1
/xmb travel all sg "Valkurm Dunes"
/xmb cancel
```

## Superwarp inspiration

AkadenTK/superwarp is BSD-3-Clause licensed and is valuable prior art for FFXI travel systems. It supports Home Points, Waypoints, Proto-Waypoints, Survival Guides and many additional retail systems, including multibox IPC. XI Command uses a clean provider interface so CatsEye-specific destinations and menu flows can be supported without importing retail-only assumptions.

See `docs/TRAVEL.md` for the design and porting plan.
