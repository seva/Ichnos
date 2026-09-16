# ichnos — Cross-Channel Context Engine (CCE)

A context engine that lets sanctioned agents and surfaces retrieve the operator's live cross-channel context on prompt over MCP — API/protocol fast-paths where they exist, an isolated-display fallback for walled gardens, and a HITL portal for authentication checkpoints.

Built on the [epistegrity](https://github.com/seva/epistegrity) methodology scaffold (pinned at `.epistegrity-version`).

## Status

L2 reached — CCE MCP server live; first consumer opencode (operator-verified), second consumer OpenClaw (gateway path, live-verified). Next rung L3: multi-channel matrix + second consumer — see `docs/scope.md` for the ladder and `IMPLEMENTATION.md` for the current state.

## Session start

Read `AGENTS.md` — it is this project's session bootstrap. `METHODOLOGY.md` holds the operating rules; `CYCLE.md` the operating loop.

## Prior incarnation

This repo began as the Mythos Footprint Detector (stylometric analysis of Glasswing-credited advisories), closed no-go at its Phase 0→1 gate. That history is preserved at tag `mythos-detector-phase0` (commit `7c67069`) and in git history; its docs were removed from the working tree as record hygiene.
