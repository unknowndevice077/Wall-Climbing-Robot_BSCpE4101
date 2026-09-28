#include "adhesion.h"

#include <Arduino.h>

#include "config.h"

static int appliedPct = -1;  // -1 = never set, so the first adhesionSetPower(0) really writes

void adhesionInit() {
  // TODO(adhesion): set up the adhesion output pin (skip if PIN_ADHESION_OUTPUT is PIN_NOT_SET).
  // TODO(hardware): adhesion method and driver unknown, see config.h.
  adhesionSetPower(0);
}

void adhesionUpdate() {
  // TODO(adhesion): ramp power, read feedback, etc.
}

void adhesionSetPower(int pct) {
  pct = constrain(pct, 0, MAX_ADHESION_POWER_PCT);
  if (pct == appliedPct) return;  // same as last time: do nothing
  appliedPct = pct;
  // TODO(adhesion): write `pct` to the adhesion output.
}

int adhesionGetPower() {
  return appliedPct < 0 ? 0 : appliedPct;
}

bool adhesionIsOk() {
  // TODO(adhesion): return true only when adhesion is really holding.
  // The stub returns false: the safe answer when we don't know.
  return false;
}
