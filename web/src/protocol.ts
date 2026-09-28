// =============================================================================
// protocol.ts — WebSocket message format. Owner: lead. Spec: docs/protocol.md
//
// Must match firmware/include/protocol.h. Changing anything here needs the lead's
// OK and a PROTOCOL_VERSION bump in BOTH files (scripts/build-web.mjs checks this).
// =============================================================================

export const PROTOCOL_VERSION = 1;

/** The UI sends a message at least this often. The robot stops the wheels after 500 ms of silence. */
export const SEND_INTERVAL_MS = 100;

// ----- client -> robot -------------------------------------------------------

/** left/right: -100..100 percent. Positive = forward (up the wall). */
export interface DriveMessage {
  type: "drive";
  left: number;
  right: number;
}

/** power: 0..100 percent. */
export interface AdhesionMessage {
  type: "adhesion";
  power: number;
}

export interface HeartbeatMessage {
  type: "heartbeat";
}

export interface EstopMessage {
  type: "estop";
}

export interface ResetEstopMessage {
  type: "reset_estop";
}

export type ClientMessage =
  | DriveMessage
  | AdhesionMessage
  | HeartbeatMessage
  | EstopMessage
  | ResetEstopMessage;

// ----- robot -> client -------------------------------------------------------

export type RobotState = "ESTOP" | "LINK_LOST" | "RUNNING";

/** Sent once when the WebSocket connects. */
export interface HelloMessage {
  type: "hello";
  protocol: number;
  firmware: string;
}

/** Sent about 10 times per second. null = sensor not available. */
export interface TelemetryMessage {
  type: "telemetry";
  protocol: number;
  firmware: string;
  state: RobotState;
  estop: boolean;
  linkOk: boolean;
  batteryV: number | null;
  adhesionPct: number;
  adhesionOk: boolean;
  motorLeftPct: number;
  motorRightPct: number;
  pitchDeg: number | null;
  rollDeg: number | null;
  uptimeMs: number;
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type RobotMessage = HelloMessage | TelemetryMessage | ErrorMessage;

/** Parse a message from the robot. Returns null for anything we don't understand. */
export function parseRobotMessage(text: string): RobotMessage | null {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const type = (data as { type?: unknown }).type;
  if (type === "hello" || type === "telemetry" || type === "error") {
    return data as RobotMessage;
  }
  return null;
}

/** Clamp and round a number into an integer range. */
export function clampPct(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.min(max, Math.max(min, value)));
}
