import type { Robot } from "../useRobot";
import { PROTOCOL_VERSION } from "../protocol";

/** Top bar: connection state and versions. Red whenever we are not connected. */
export function ConnectionStatus({ robot }: { robot: Robot }) {
  const { connection, firmwareVersion, protocolVersion, url } = robot;
  const connected = connection === "connected";
  const versionMismatch = firmwareVersion !== null && firmwareVersion !== __APP_VERSION__;
  const protocolMismatch = protocolVersion !== null && protocolVersion !== PROTOCOL_VERSION;

  return (
    <header className={`status ${connected ? "status-ok" : "status-bad"}`} role="status">
      <strong>{connected ? "● Connected" : connection === "connecting" ? "● Connecting…" : "● DISCONNECTED"}</strong>
      <span className="status-versions">
        UI {__APP_VERSION__} · Robot {firmwareVersion ?? "?"}
      </span>
      {!connected && <span className="status-detail">Reconnecting to {url}. Wheels stop automatically.</span>}
      {(versionMismatch || protocolMismatch) && (
        <span className="status-detail status-warning">
          Version mismatch: upload BOTH the filesystem image and the firmware (see README).
        </span>
      )}
    </header>
  );
}
