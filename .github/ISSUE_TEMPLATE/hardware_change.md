---
name: Hardware change
about: Propose a new part, a wiring change, or a pin change
title: "[hardware] short description"
labels: hardware
assignees: ''
---

## What do you want to change?
<!-- e.g. "Use GPIO 25 for the left motor PWM", "Add a VL53L0X distance sensor" -->

## Why?

## Details
- Part name / model (with datasheet link):
- Pins affected (old → new):
- Voltage / current:
- Library needed (name + exact version):

## Affects which modules?
- [ ] locomotion  - [ ] adhesion  - [ ] sensors  - [ ] comms / web  - [ ] main

## Safety impact
<!-- Could this make the robot fall, move unexpectedly, or overheat? -->

## Checklist (after approval)
- [ ] Lead approved this issue
- [ ] `firmware/include/config.h` updated (and `TODO(hardware)` removed)
- [ ] `firmware/platformio.ini` `lib_deps` updated (exact version) if a library was added
- [ ] Decision recorded in `docs/decisions.md`
