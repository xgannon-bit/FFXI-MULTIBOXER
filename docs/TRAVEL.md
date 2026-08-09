# Travel subsystem

## Objective

Make moving multiple local characters feel like moving one party. The controller issues one travel intent, resolves which local clients should participate, staggers menu interaction, waits for acknowledgements, and reports exceptions such as a locked destination or a character that failed to zone.

## Prior art

AkadenTK/superwarp is BSD-3-Clause licensed and supports a broad set of FFXI travel systems. Useful design ideas we are carrying forward conceptually:

- one common command prefix
- destination aliases / fuzzy destination resolution
- `all` / `party` multibox scopes
- per-character stagger delay for simultaneous menu systems
- missing/unlocked destination reporting
- cancel/reset behavior
- smart context-sensitive travel commands

XI Command does **not** blindly copy retail warp tables or assume Windower packet layouts. CatsEye can differ from retail and this project targets Ashita v4 first.

## Supported command model

```text
TRAVEL <system> <destination> [sub_destination]
```

Initial system identifiers:

| ID | System |
|---|---|
| `hp` | Home Point |
| `wp` | Waypoint |
| `pwp` | Proto-Waypoint |
| `sg` | Survival Guide |
| `ew` | Escha / Reisenjima |
| `un` | Unity |
| `ab` | Abyssea |
| `po` | Runic Portal |
| `vw` | Voidwatch |
| `so` | Sortie |
| `od` | Odyssey |
| `li` | Limbus |

CatsEye availability will be discovered and gated per provider. Unsupported retail-only systems must return `UNSUPPORTED`, not attempt a menu sequence.

## Provider interface

The in-game agent will expose travel providers with these operations:

```text
can_handle(system, zone)
resolve(destination, sub_destination)
preflight(resolved_destination)
begin(resolved_destination)
tick()
cancel()
status()
```

`preflight` should validate as much as possible before touching a menu:

- correct zone / nearby NPC
- destination known/unlocked when that information is available
- required currency/key item
- not currently zoning
- not in a conflicting menu/event

## Multibox flow

```text
player issues travel request
        |
        v
controller resolves scope
        |
        v
preflight each character
        |
        +---- blocked clients -> UI warning
        |
        v
leader-last ordered queue
        |
        v
client A begin ---- ACK
    300ms
client B begin ---- ACK
    300ms
leader begin ------ ACK
        |
        v
watch zone/menu completion
        |
        v
party regroup / exception report
```

Default leader-last ordering is intentional: the player keeps control of the main window while boxes start their menu interaction.

## Safety / attended boundary

Travel is allowed only from an explicit user/controller request or another explicitly approved attended workflow. There is no autonomous route planner that repeatedly farms, pulls, claims or levels by itself.

## Next implementation work

1. Capture CatsEye/Ashita menu + packet traces for Home Points and Survival Guides.
2. Implement `HomePointProvider` and `SurvivalGuideProvider` using normal menu-state transitions.
3. Add destination unlock tracking.
4. Add aliases/fuzzy search.
5. Add `travel all ...` preflight summary and retry UI.
6. Add same-zone arrival verification and party regroup.
