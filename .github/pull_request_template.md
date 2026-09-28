## What changed
<!-- 1–3 sentences. What does this PR do and why? -->

Closes #

## Area
<!-- Tick one (or more if the lead asked for it). -->
- [ ] main / integration (lead)
- [ ] config (`config.h`): **needs lead approval**
- [ ] locomotion
- [ ] adhesion
- [ ] sensors
- [ ] comms (firmware networking)
- [ ] web UI
- [ ] protocol (`docs/protocol.md`, `protocol.h/.cpp`, `protocol.ts`): **needs lead approval**
- [ ] docs / CI / other

## Shared things changed?
- [ ] No, I only changed files in my own area
- [ ] Yes, I changed a shared interface (`.h` function or struct field): explained below
- [ ] Yes, I changed a pin or constant in `config.h`: explained below
- [ ] Yes, I changed the protocol, and updated docs + firmware + web together (and `PROTOCOL_VERSION` if needed)

## How was it tested?
- [ ] Firmware builds (`pio run`)
- [ ] Web builds (`npm run build`)
- [ ] PC tests pass (`pio test -e native`), if logic changed
- Tested on real hardware? **yes / no**
  - [ ] I uploaded **both** the filesystem image and the firmware (no version mismatch in the UI)
- What I did and what I saw:
<!-- e.g. "On the bench: reset e-stop, pushed joystick forward, left wheel spun forward at 30%. Turned off phone WiFi, wheels stopped." -->

## AI use
- [ ] I did not use AI for this PR
- [ ] I used AI (tool: ______ ) **and** I understand every line and can explain it in review

## Safety checklist
- [ ] Link-loss failsafe still works (no messages for 500 ms → wheels stop, adhesion keeps running)
- [ ] E-STOP still latches until `reset_estop`; the UI E-STOP button is still always visible
- [ ] Incoming values are still clamped; `MAX_MOTOR_POWER_PCT` not raised without lead approval
- [ ] No `delay()` or blocking loops in the control task or `...Update()` functions
- [ ] WebSocket code doesn't call motor/adhesion code directly (goes through shared state)
- [ ] No hard-coded pins or magic numbers (they are in `config.h`), no secrets committed
- [ ] Anything that moves was tested on the bench before the wall (see SAFETY.md)
