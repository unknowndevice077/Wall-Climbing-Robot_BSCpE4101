# SAFETY

A wall-climbing robot can fall, drive unexpectedly, or throw debris from a fan.
These rules are **not optional**. If something feels unsafe, stop and tell the lead.

## Rules

1. **Adhesion stays ON while the robot is on the wall.**
   The firmware never cuts adhesion on its own: not on e-stop, not on link loss. Only the operator can lower it,
   and the UI asks for confirmation before setting it to 0. Only turn adhesion off when someone is **holding the
   robot** or it is on the ground.
   Note: if the ESP32 reboots or loses power, adhesion stops. That is what the tether is for.

2. **Link-loss failsafe (firmware, mandatory).**
   The UI sends a `heartbeat` or `drive` message every ~100 ms. If the robot receives nothing for
   `LINK_TIMEOUT_MS` (500 ms, in `config.h`), it **stops the wheels but keeps adhesion running**.
   A drive command older than 500 ms is ignored even if heartbeats keep coming.
   Test it every session: turn off the phone's WiFi while driving on the bench, and the wheels must stop.

3. **E-STOP (firmware + UI, mandatory).**
   - The UI has a large, always-visible **E-STOP** button. The robot **latches** e-stop: wheels stop, adhesion is
     frozen at its current power, and nothing moves until someone presses **Reset E-STOP** (explicit `reset_estop`).
   - The robot **boots in E-STOP**.
   - The UI turns **red** when disconnected. If you press E-STOP while disconnected, it can't be delivered,
     so use the physical kill switch.

4. **A physical kill switch is still required.** The web UI is **not** a replacement: WiFi can drop, phones
   freeze, batteries die. A physical way to cut power must be within reach of the operator in every test.
   TODO(hardware): decide the kill switch and whether it cuts drive motors only or also adhesion
   (cutting adhesion on the wall = robot falls, so the tether must catch it).

5. **Motor power limit during testing.**
   The firmware clamps every incoming value, and `MAX_MOTOR_POWER_PCT` in `config.h` caps wheel power
   (currently **30%**). Only the lead may raise it, and only after testing at the lower limit.

6. **Always use a tether and a spotter on the wall.**
   - The tether (safety line) must hold the robot's full weight and stop it before it hits the floor.
     TODO(hardware): decide the tether type and attachment point.
   - A spotter stands ready to catch the robot and does nothing else. The operator is a different person.

7. **Bench first, then wall.** Test every new code change on the bench (wheels off the ground) before the wall.

8. **Power and batteries.** TODO(hardware): battery type is unknown. Add charging/storage rules once chosen
   (for LiPo: never unattended, fire-safe bag, no damaged/puffy packs).

9. **Fans and moving parts.** Keep fingers, hair, cables, and loose clothing away from wheels and any fan/impeller.
   Wear eye protection near a spinning fan.

10. **Never disable safety code** (link-loss failsafe, e-stop latch, value clamping, power limit) to
    "just test something".

## Checklist before EVERY wall test

Tick each line out loud.

**People**
- [ ] Operator named: ________  Spotter named: ________
- [ ] Everyone knows where the E-STOP button and the **physical kill switch** are

**Robot**
- [ ] Firmware **and** filesystem image uploaded from the same commit: UI top bar shows no *version mismatch*
- [ ] Battery charged and undamaged, wiring secure, nothing loose
- [ ] Tether attached and checked (pull test)
- [ ] `MAX_MOTOR_POWER_PCT` is the approved value

**Bench test (robot held / wheels off the ground)**
- [ ] UI shows **Connected** (green) and telemetry is updating
- [ ] Robot starts in `ESTOP`; wheels don't move until **Reset E-STOP**
- [ ] E-STOP button → `ESTOP`, wheels stop, stays stopped until reset
- [ ] Link loss (turn off phone WiFi while driving) → wheels stop within 0.5 s, adhesion keeps running, UI turns red
- [ ] Physical kill switch works
- [ ] Adhesion turns on and `adhesionOk` reports correctly
- [ ] Wheels spin the right direction at low power

**Wall**
- [ ] Wall surface clean and dry, floor below clear of people and objects
- [ ] Phone/laptop close to the robot (strong WiFi)
- [ ] Start low (hand-height) before going higher
- [ ] Spotter ready → start

**After**
- [ ] Robot held by spotter → adhesion 0 → power off
- [ ] Problems written down as GitHub issues
