# Copilot instructions

Read and follow [AGENTS.md](../AGENTS.md) in the repository root before doing anything.
It is the single source of truth for this project: hardware, folder ownership, architecture, interfaces,
build commands, coding style, safety rules, and git rules. If anything here conflicts with
AGENTS.md, AGENTS.md wins.

Most important:
- Never invent hardware details. Unknown = `TODO(hardware)`.
- Pins, constants and network settings only in `firmware/include/config.h`.
- Only edit your own area. Never break shared interfaces (`firmware/include/*.h`) or the protocol
  (`docs/protocol.md`) silently.
- Only the comms module touches networking; WebSocket code never calls motor code directly.
- Never weaken the link-loss failsafe, e-stop latch, or value clamping.
- Work on a feature branch, never on `main`.
