# XI Command Integration-First Strategy

XI Command should **orchestrate proven FFXI addons instead of reimplementing solved behavior**.

## Why this pivot

The original bootstrap targeted the CatsEye launcher / Ashita v4 environment directly, so the first design assumed XI Command needed native implementations for travel, follow, combat roles and menu driving. That is useful as a fallback, but it duplicates mature FFXI work.

CatsEye supports manual Windower clients as well as Ashita. For the multibox test build, the fastest path to a powerful system is therefore:

1. Use mature addons as providers where their behavior is already correct.
2. Keep XI Command as the cross-character coordinator, safety gate, profile manager, telemetry layer and UI.
3. Write native code only for missing behavior or where an existing addon cannot be legally redistributed/integrated.

## Provider stack

### Superwarp provider — travel

Use the user's separately installed `AkadenTK/superwarp` for Home Points, Survival Guides, Waypoints, Proto-Waypoints and other supported travel systems.

XI Command does **not** need to reproduce Superwarp menu/packet logic. It only needs to resolve scope + destination and issue the public Superwarp command on each intended local character.

Examples:

```text
//sw hp all "Ru'Lude Gardens" 1
//sw sg party "Valkurm Dunes"
```

XI Command still adds value around Superwarp by tracking which local clients are online, leader-last behavior where useful, travel sessions, success/failure telemetry and regroup logic.

### Trust provider — combat roles

Use the user's separately installed `cyritegamestudios/trust` as an **external dependency**, controlled only through its documented commands.

Trust already provides mature implementations of:

- follow / assist
- auto engage and mirrored engage state
- job logic for all 22 jobs
- healing and status removal
- songs and rolls
- weapon skills and skillchains
- automatic magic bursts
- MP restoration behavior
- multi-box IPC

Important licensing rule: Trust's current license allows personal use/reference but prohibits redistribution, forks and derivative works without permission. XI Command therefore MUST NOT vendor, copy or modify Trust source unless written permission is obtained from Cyrite. The integration is command-level only.

### XI Command native provider — missing glue

XI Command owns the behavior that existing addons do not solve cleanly:

- attended encounter authorization / no-pull gate
- unified profiles across addons and characters
- cross-addon orchestration
- centralized duplicate-action reservations where needed
- automatic resting policy for MP jobs if Trust does not satisfy the desired /heal behavior
- travel-to-follow handoff after zoning
- per-character role presets
- safety modes for CatsEye test rules
- telemetry, dashboard, replay and diagnostics
- optional native replacements if a dependency is unavailable

## Runtime architecture

```text
XI Command Desktop / Core
        |
        | localhost command protocol
        v
Windower XICommandBridge.lua (one per FFXI instance)
        |
        +--> Trust public commands
        +--> Superwarp public commands
        +--> Windower / FFXI commands
        +--> XI Command native micro-behaviors
```

The Windower bridge is intentionally thin. It should not contain a second healer, second skillchain engine, or second travel implementation when the selected provider already owns that behavior.

## First playable CatsEye profile

Main: tank / manually controlled

Alts:

```text
Follow main                -> Trust
Assist main                -> Trust
Mirror tank engage state   -> Trust AutoEngageMode Mirror
Auto skillchain            -> Trust AutoSkillchainMode Auto
Auto magic burst           -> Trust AutoMagicBurstMode Auto
MP recovery abilities      -> Trust AutoRestoreManaMode Auto
Auto rest between fights   -> XI Command native rest policy if needed
Warp together              -> Superwarp
```

Pulling and autonomous target acquisition remain disabled in the CatsEye test profile.

## Development priority

1. Windower bridge + provider command adapters.
2. Trust profile application.
3. Superwarp scope/destination integration.
4. Native MP rest policy.
5. Zone/follow recovery.
6. Unified dashboard and telemetry.
7. Only then build native replacements for gaps we discover during testing.
