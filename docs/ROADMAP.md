# XI Command Development Roadmap

## Project principle

XI Command is an attended multibox orchestration platform for CatsEyeXI/Ashita. It may automate support, movement, positioning, skillchains, magic bursts, interrupts, buffs, travel, and other explicitly approved actions while the player is present. The normal build does not contain autonomous claiming, pulling, AFK farming, or AFK leveling loops.

## Milestone M0 - Bootstrap and protocol
Status: complete

- Repository layout
- Versioned wire protocol
- UDP controller skeleton
- Agent command parser
- Manual encounter arm/disarm gate
- Travel request model
- Staggered multibox dispatch

Exit criteria: controller and addon have stable message/command vocabulary.

## Milestone M1 - Core orchestration engine
Status: in progress

Goal: make the desktop controller independently testable before live game integration.

Features:
- Character registry with online/offline timeout
- Structured character state model
- Encounter session state machine
- Hard manual authorization gate
- Intent model and arbitration
- Resource reservation to prevent duplicate cure/stun/WS actions
- Command ledger with ACK/timeout tracking
- Travel sessions with per-character progress
- Structured telemetry/event log
- Simulation harness and unit tests

Exit criteria:
- Two or more simulated agents can register and update state.
- Controller blocks combat commands while disarmed.
- Competing intents select one deterministic winner.
- Reservations prevent duplicate actions.
- Travel session tracks queued/sent/acked/failed participants.
- All pure-Python tests pass without FFXI installed.

## Milestone M2 - Ashita transport and live telemetry
Goal: connect real CatsEye clients to the tested controller.

Features:
- Ashita UDP transport
- HELLO/heartbeat/state publishing
- CMD receive + ACK result reporting
- Character HP/MP/TP/zone/target/position state
- Local command execution adapter
- Developer HUD and transport diagnostics
- Reconnect/re-register behavior after zoning

Exit criteria: two live CatsEye clients appear in the controller and accept safe diagnostic commands.

## Milestone M3 - Superwarp travel provider
Goal: synchronized multi-character travel.

Features:
- Home Point provider
- Survival Guide provider
- Waypoint / Proto-Waypoint provider where CatsEye supports them
- Destination aliases and fuzzy resolver
- Per-character unlock/preflight results
- leader-last dispatch
- arrival detection and regroup status
- cancel/retry handling
- smart travel command based on nearby valid travel NPC

Exit criteria: one command moves all selected local characters through an approved travel system and verifies arrival.

## Milestone M4 - Formation and movement engine
Goal: make boxes position themselves intelligently after the player initiates an encounter.

Features:
- Follow / hold / regroup
- role distance bands
- tank/front, melee/rear, healer/ranged anchors
- formation templates: stack, line, spread, boss
- movement deadband to prevent jitter
- stuck detection and recovery
- post-zone regroup

Exit criteria: boxes maintain assigned relative positions through a normal fight without oscillation.

## Milestone M5 - Support AI
Goal: useful RDM/WHM/BRD/COR support automation.

Features:
- cure scoring
- status removal
- haste/refresh/buff uptime
- dispel/debuff logic
- MP conservation
- spell/JA recast checks
- emergency priorities
- centralized heal arbitration

Exit criteria: support boxes act without duplicate cures or conflicting actions.

## Milestone M6 - Combat coordinator
Goal: party-level coordination rather than independent bots.

Features:
- TP reservation
- weaponskill planner
- automatic skillchain execution
- magic burst timing
- stun/interrupt rotation
- duplicate-action suppression
- role-aware target synchronization

Exit criteria: three-character simulated party executes a deterministic SC+MB and interrupt rotation.

## Milestone M7 - Encounter profiles and UI

- PySide6 dashboard
- role editor
- encounter profiles
- visual priority/behavior editor
- live intent queue
- action history
- warnings and emergency controls

## Milestone M8 - Analytics and replay

- SQLite combat telemetry
- buff/debuff uptime
- healing/overheal analysis
- interrupt response time
- skillchain timing quality
- replay timeline
- offline profile tuning

## Development order

Work vertically: each milestone must leave XI Command more usable than before. Core logic remains deterministic and unit-testable. Game-specific code is isolated behind adapters/providers so CatsEye menu and packet details do not contaminate the decision engine.
