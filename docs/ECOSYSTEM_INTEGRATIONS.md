# XI Command Ecosystem Integration Matrix

XI Command should be a modern multibox control center, not a collection of rewrites of mature FFXI addons. The rule is: **integrate solved behavior, own cross-character orchestration, build only the missing glue or features that require a centralized party view.**

## Core provider stack

| Capability | Primary provider | XI Command responsibility |
| --- | --- | --- |
| Travel | Superwarp | destination UI, scope selection, session status, post-zone regroup |
| General job/combat AI | Trust | role/profile configuration, ownership rules, encounter gate, coordination |
| Healing | CurePlease CE | assign healer ownership, party-wide reservations, expose CPCE settings in XI Command |
| Resting / recovery | XI Command native | MP thresholds, stand/rest state, recovery sequencing |
| Gear changes | GearSwap | load/validate job profiles, health/status surfaced in dashboard |
| Cross-client command transport | Windower Send / Trust IPC | provider dispatch; XI Command adds typed command/state coordination |

## Existing community components to integrate rather than rewrite

### Windower Sandbox
Required/recommended baseline for multibox clients because it fixes issues caused by shared resources between FFXI instances. XI Command should detect whether it is loaded and warn when multiple clients are present without it.

### WinControl
Can move/resize game windows. XI Command should expose modern layouts: Main + sidecars, 2x2, 3-client vertical, focus-main, and restore-layout. We may later replace command-level integration with native Windows window management if that gives smoother focus/layout control.

### AutoJoin
Useful for automatically accepting party/alliance invites from whitelisted characters. XI Command should provide a party-session button that configures/invokes AutoJoin rather than recreating invite acceptance first.

### GearSwap
Foundation for per-job equipment behavior and also a Trust dependency. XI Command should treat GearSwap as a required provider for Trust-based combat profiles and report whether each character has a valid loaded job profile.

### Organizer + Itemizer
Inventory/gear preparation providers. XI Command can provide a "Ready Check" that asks each client whether required gear, food, ammo, tools and free inventory space are available, then invokes Organizer/Itemizer where appropriate.

### Treasury
Potential loot provider. XI Command should not duplicate its lot/pass/drop mechanics. A future Loot Director can assign ownership rules centrally and configure Treasury per character. Enable only under server-approved attended behavior.

### ChatPorter
Existing cross-character chat forwarding. XI Command may integrate it initially, but a native aggregated event/chat panel is likely a worthwhile later replacement because XI Command already receives state from every client.

### FindAll
Useful inventory lookup across characters. XI Command should expose a global item search and can invoke/query FindAll instead of implementing a second inventory index initially.

### Timers / TParty / Distance
Useful existing visual information, but XI Command should eventually supersede their multibox use case with a single cross-character dashboard showing TP, recasts, buffs, target distance, current action and alerts without requiring overlays on every alt window.

### Specialist job addons
AutoCOR, Singer, AutoGEO, AutoRA and similar tools remain useful fallback providers if Trust behavior on a particular job is weaker than a specialist addon. XI Command should use a capability-provider registry so a user can choose, for example, Trust or AutoCOR for COR without changing the rest of the party architecture.

## Features XI Command should own because existing addons do not solve them well as a whole

### 1. Capability ownership / conflict prevention
Exactly one provider owns each capability per character: healing, status removal, buffs, melee, WS, SC, MB, follow, travel, resting, interrupts, loot, etc. XI Command prevents Trust and CurePlease CE from issuing overlapping cures or multiple providers from fighting over movement.

### 2. Party Session Manager
One-click setup for all local characters: detect clients, identify main, assign roles, verify party/zone, configure providers, apply follow/assist relationships, disable pulling, validate profiles, and show READY / DEGRADED / OFFLINE.

### 3. Global Ready Check
For every character: online, same zone, correct job/subjob, HP/MP, required providers loaded, GearSwap profile loaded, food/ammo/tools available, inventory space, follow target, combat ownership, and travel readiness.

### 4. Cross-character action reservations
Central reservations for Cure, Stun, Dispel, Raise, status removal, WS/SC steps and MB windows. This is one of XI Command's largest advantages over independent addons.

### 5. Encounter lifecycle
TRAVEL -> FORM -> READY -> COMBAT -> RECOVERY -> REGROUP. Main player initiates/authorizes the encounter; XI Command coordinates providers afterward. No autonomous claim/pull/farm loop in the normal CatsEye profile.

### 6. Recovery Director
When combat ends or a character dies: disengage/stand, raise if applicable, wait for weakness policy, cure, restore MP, rebuff, reapply songs/rolls, resume follow, and mark party READY again.

### 7. Window / focus manager
Modern desktop controls for 2-6 clients: layout presets, main-focus hotkey, cycle characters, identify window, picture-in-picture sidecars, and optional controller/Stream Deck actions.

### 8. Unified multibox HUD
One view for all clients: HP/MP/TP, role, distance from main, target, action, buffs/debuff warnings, recasts, provider state, resting, dead/weakness, SC plan, MB window, travel state and warnings.

### 9. Encounter profiles
Profiles such as Leveling, Boss, Travel, Recovery, Melee Burn, Caster Party. A profile changes multiple providers at once instead of requiring dozens of addon commands.

### 10. Dependency and health manager
Detect Windower, Send, Sandbox, Trust, Superwarp, CurePlease CE bridge, GearSwap and optional providers. Show version/status and provide one-click configure/load/reload actions. Never silently assume an addon is working.

### 11. Modern input layer
Global hotkeys/gamepad/Stream Deck support independent of the active FFXI window. Examples: Follow/Hold, Regroup, Travel Party, Emergency Stop, Focus Main, Pause Healer, Burst On/Off, SC Mode, Recovery, Party Ready Check.

### 12. Telemetry and replay
One synchronized timeline across all local characters: actions, HP changes, cures, WS, SC/MB, interrupts, position, provider decisions and failures. This lets us tune multibox behavior scientifically instead of guessing.

## Target experience

A user should launch XI Command, select a party profile, and see:

```text
PARTY: PLD + RDM + DRG
Main: Gannon

Gannon      PLD   READY   Trust/GearSwap
Coughdrop   RDM   READY   Trust + CurePlease CE
AltThree    DRG   READY   Trust/GearSwap

Travel      Superwarp       READY
Follow      Trust IPC       READY
Healing     CurePlease CE   READY
SC/MB       Trust           READY
Rest        XI Command      READY
Sandbox                     READY

[START PARTY SESSION] [TRAVEL] [REGROUP] [RECOVERY] [STOP ALL]
```

The user chooses roles and goals; XI Command translates that into the correct provider configuration and continuously detects conflicts/failures.