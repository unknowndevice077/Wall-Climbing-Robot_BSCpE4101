# Starter task backlog

Each task below can be pasted straight into a new GitHub Issue
(use the **Task** template; the `###` heading is the issue title).
Tasks marked **needs hardware** can't be finished until that `TODO(hardware)` is decided.
Every task is done only when CI is green and the PR is approved.

---

## Lead / integration

### [main] Fill in the hardware facts in config.h and decisions.md
Collect the chosen parts and pins from each owner (via Hardware change issues), update
`firmware/include/config.h`, remove the matching `TODO(hardware)` lines, and log each decision in `docs/decisions.md`.
**Done when:** no `TODO(hardware)` is left for parts that are already chosen. **Needs hardware.**

### [main] Decide what happens when adhesion fails
Right now the firmware only *reports* `adhesionOk`. Decide with the adhesion owner what the robot should do when
adhesion is on but `adhesionIsOk()` is false (e.g. stop the wheels after X ms?). Update the state machine and add PC tests.
**Done when:** the decision is in `docs/decisions.md`, implemented, and tested in `test_state_machine`.

### [main] Allow only one controller at a time
Two phones connected at once could both drive. Decide the rule (first client wins? last one?) and implement it
in shared state/comms with the control/UI owner. **Done when:** a second phone can watch telemetry but not drive.

### [main] Add a status LED showing the robot state
Blink `PIN_STATUS_LED` with a different pattern per state (ESTOP fast, LINK_LOST slow, RUNNING solid) from the
control task. Skip if `PIN_NOT_SET`. No `delay()`. **Done when:** each state is visible on the LED. **Needs hardware.**

### [main] Warn if the control loop runs late
Measure how long each control loop iteration takes. If it is longer than `CONTROL_LOOP_PERIOD_MS`, count it and
report the count in telemetry (protocol change: update all 4 protocol files).
**Done when:** the counter goes up if you temporarily add a slow loop in a module stub.

---

## Locomotion

### [locomotion] Research the motor driver and propose the pin plan
Find the datasheet of the chosen motor driver. Write which ESP32 pins you need (PWM, direction, ...) and open a
**Hardware change** issue. Don't edit `config.h` yourself. **Done when:** the lead approved the pin plan. **Needs hardware.**

### [locomotion] Set up the motor pins in locomotionInit()
In `firmware/src/locomotion/locomotion.cpp`, set the motor pins as outputs and set up PWM with `ledcSetup()` +
`ledcAttachPin()` (core 2.0.17 API). Skip pins that are `PIN_NOT_SET`. Motors must be stopped at the end.
**Done when:** it builds, and on the bench the motors don't twitch at power-up. **Needs hardware.**

### [locomotion] Implement setMotorSpeed() and stopMotors()
Convert `-100..100 %` into PWM duty and direction for each side. Keep the existing clamping.
**Done when:** on the bench (wheels off the ground), forward on the joystick spins both wheels forward.

### [locomotion] Add a direction-invert setting for each motor
If a motor is mounted backwards, forward spins it the wrong way. Propose `MOTOR_LEFT_INVERTED` /
`MOTOR_RIGHT_INVERTED` constants for `config.h` (ask the lead) and use them. **Done when:** flipping the constant flips the wheel.

### [locomotion] Ramp speed changes smoothly
Jumping from 0 to full speed can make wheels slip on the wall. Limit how fast the output can change per loop
(no `delay()`). **Done when:** a sudden joystick push ramps up over a short time agreed with the lead.

---

## Adhesion

### [adhesion] Research the adhesion hardware and propose pins
Find the datasheet for the chosen fan/pump/magnet and its driver (ESC, MOSFET, ...). Open a **Hardware change**
issue with wiring, pins, and power needs. **Needs hardware.**

### [adhesion] Implement adhesionSetPower()
Drive `PIN_ADHESION_OUTPUT` at the given percent. It's called **every 10 ms** with the same value, so only write to the
hardware when the value changes (already handled by the stub). Skip if `PIN_NOT_SET`.
**Done when:** on the bench, the web UI slider changes the adhesion power. **Needs hardware.**

### [adhesion] Soft start in adhesionUpdate()
Ramp power up gradually instead of jumping to the new value (less current spike). The ramp time becomes a
constant in `config.h` (lead approval). **Done when:** the power visibly/audibly ramps up.

### [adhesion] Decide how we know adhesion is working
How can `adhesionIsOk()` know the robot is really holding? (pressure sensor, current draw, ...?) Write a proposal in
the issue, discuss with the sensors owner and the lead. **Done when:** the method is in `docs/decisions.md`.

### [adhesion] Implement adhesionIsOk()
Use the agreed method. Return `false` whenever you are unsure.
**Done when:** telemetry shows "(ok)" only when adhesion is really on and working (bench test).

---

## Sensors

### [sensors] List the sensors we need and have
Which sensors are useful (tilt/IMU, battery voltage, adhesion pressure, distance, ...), which ones we actually
have, and their interface (I2C, analog, ...)? Open **Hardware change** issues for the ones we'll use.
**Done when:** the lead approved the sensor list. **Needs hardware.**

### [sensors] Measure the battery voltage
Read `PIN_BATTERY_ADC` through the voltage divider and fill `batteryV` / `batteryValid`. Average a few readings.
**Done when:** the web UI shows a voltage within 0.2 V of a multimeter. **Needs hardware** (battery + divider).

### [sensors] Start the I2C bus and scan for devices
In `sensorsInit()`, start `Wire` on `PIN_I2C_SDA` / `PIN_I2C_SCL` (skip if `PIN_NOT_SET`) and print every device
address found to Serial. **Done when:** the Serial Monitor lists the connected sensors. **Needs hardware.**

### [sensors] Read the IMU and fill pitchDeg / rollDeg
Read the IMU in `sensorsUpdate()` and fill `pitchDeg`, `rollDeg`, `tiltValid`. On a read error set `tiltValid = false`
(don't crash, don't block). New library → ask the lead, add it to `lib_deps` with an exact version.
**Done when:** the web UI shows sensible angles when you tilt the robot by hand. **Needs hardware.**

### [sensors] Filter the tilt readings
Raw IMU angles are noisy. Add a simple filter (moving average or complementary filter).
**Done when:** telemetry angles are steady when the robot is still, and still follow movement.

---

## Control / UI

### [web] Connection status indicator: show signal quality
The status bar already shows connected/disconnected. Add the time since the last telemetry message (or messages/s)
so the operator sees a weak link *before* it drops. Keep it red when disconnected.
**Done when:** walking away from the robot visibly degrades the indicator before it disconnects.

### [web] Joystick component: dead zone and slow mode
Add a small dead zone in the middle (so a resting thumb doesn't creep) and a "slow" toggle that halves the output.
**Done when:** tested on a phone, a light touch in the centre sends 0, slow mode sends half.

### [web] Telemetry panel: highlight problems
Colour values that need attention: battery low (threshold from the lead), `adhesionOk` false while adhesion is on,
`linkOk` false. Keep it readable on a phone in sunlight. **Done when:** each warning shows up when faked in the code.

### [web] Reconnect logic: test and harden
Test `useRobot.ts` reconnect with: robot reboot, walking out of WiFi range, phone screen lock/unlock, and
switching tabs. Fix anything that doesn't recover. **Done when:** all four cases recover automatically; list results in the PR.

### [web] Mock robot for UI development
Write a small Node script (`scripts/mock-robot.mjs`) that speaks the protocol (sends `hello` + `telemetry`,
accepts commands) so the UI can be developed without the ESP32. Ask the lead before adding any npm package.
**Done when:** `npm run dev` with `VITE_ROBOT_WS_URL=ws://localhost:8080/ws` works against the mock.

### [comms] Log WiFi and client info
Print the robot's IP, the number of connected clients, and client IPs to Serial when they change.
**Done when:** connecting a phone prints its IP in the Serial Monitor.
