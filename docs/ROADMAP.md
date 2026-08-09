# XI Command Development Roadmap

## Project principle

XI Command is an attended multibox orchestration platform for CatsEyeXI. It should **reuse mature FFXI addons as providers instead of rebuilding solved behavior**. CatsEye supports manual Windower or Ashita clients; the primary multibox test path is now Windower because the strongest existing travel/combat automation ecosystem is there.

The normal CatsEye test profile does not contain autonomous claiming, pulling, AFK farming, or AFK leveling loops.

See `INTEGRATION_STRATEGY.md` for the provider model.

## Milestone M0 - Bootstrap and protocol
Status: complete

- Repository layout
- Versioned wire protocol
- Controller skeleton
- Manual encounter arm/disarm gate
- Travel request model
- Staggered multibox dispatch

## Milestone M1 - Core orchestration engine
Status: complete enough for provider integration

- Character registry/state model
- Encounter session state machine
- Manual authorization gate
- Intent model and arbitration
- Resource reservations
- Command ledger with ACK/timeout tracking
- Travel sessions
- Telemetry/event log
- Offline simulation harness and tests

## Milestone M2 - Existing-addon integration layer
Status: in progress

Goal: get a powerful playable multibox system quickly by controlling proven addons.

### Superwarp provider
- Delegate Home Points, Survival Guides, Waypoints, Proto-Waypoints and other supported travel to separately-installed Superwarp.
- XI Command owns scopes, travel sessions, retries, telemetry and regrouping; Superwarp owns the actual FFXI menu/warp implementation.

### Trust provider
- Treat `cyritegamestudios/trust` as an external dependency; do not vendor or derive from its source without written permission from its author.
- Apply documented Trust modes/commands for:
  - follow and assist
  - mirrored engage state
  - job automation
  - healing/status removal
  - songs/rolls
  - automatic skillchains
  - automatic magic bursts
  - MP restoration
- Hard-disable AutoPullMode in the CatsEye profile.

### Native micro-providers
Only implement missing glue:
- classic `/heal` auto-rest policy between fights
- encounter authorization
- provider state/profile coordination
- post-zone follow recovery
- diagnostics

Exit criteria: one command configures two alts to follow/assist the main, mirror main engagement, SC/MB according to job, recover MP, and use Superwarp for synchronized travel.

## Milestone M3 - Windower XI Command bridge

Goal: thin per-client bridge between XI Command and existing providers.

Features:
- one small Windower addon per FFXI process
- state heartbeat: HP/MP/TP/zone/status/target/position
- execute provider commands locally
- Windower IPC discovery/broadcast
- command ACK/result reporting
- provider availability detection (`trust`, `superwarp`, optional addons)
- reconnect/re-register after zoning

Exit criteria: two live Windower/CatsEye clients appear in XI Command and report which providers are installed.

## Milestone M4 - Playable multibox profile

Goal: make the common tank + alt(s) workflow work end-to-end.

Default behavior:
- main is manually controlled
- alts follow main
- alts assist main
- alts engage only after/mirroring main engagement
- pulling/independent target acquisition disabled
- melee jobs automatically skillchain when configured
- mage jobs automatically magic burst when configured
- support jobs use Trust role logic
- MP jobs rest between fights when configured
- all local characters warp through Superwarp
- post-zone follow automatically resumes

Exit criteria: normal attended leveling/adventuring loop works without manually swapping windows for routine alt actions.

## Milestone M5 - Safety and coordination layer

- provider-aware start/stop emergency button
- explicit combat-active gate
- target ownership checks
- duplicate command suppression
- per-role action locks where Trust does not already coordinate them
- combat ends -> disengage/recover/rest/follow state
- travel cancels combat behaviors before menu interactions

## Milestone M6 - Advanced combat additions

Only build features not already satisfactory in Trust or another approved dependency:
- cross-character stun rotation
- custom skillchain plan override
- burst reservations across multiple mages
- encounter-specific positioning
- rear/flank formation corrections
- role-specific hold distances
- boss reaction profiles

Do not rewrite Trust's full 22-job logic unless there is a concrete CatsEye compatibility gap.

## Milestone M7 - Dashboard and profile editor

- PySide6 dashboard
- provider status per character
- role presets
- enable/disable modes by job
- travel controls
- emergency stop
- live target/engage/follow state
- action history

## Milestone M8 - Analytics and replay

- SQLite telemetry
- buff/debuff uptime
- healing/overheal analysis
- interrupt timing
- skillchain timing
- travel failures
- replay timeline

## Development rule

Before implementing a game mechanic, check whether a mature addon already solves it. If yes, prefer a provider/adapter. XI Command should become the **orchestrator and UX layer**, not a collection of rewritten FFXI addons.
