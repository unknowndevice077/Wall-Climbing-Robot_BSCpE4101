import type { TelemetryMessage } from "../protocol";

function show(value: number | null, unit: string): string {
  return value === null ? "n/a" : `${value}${unit}`;
}

/** Live values from the robot (about 10 updates per second). */
export function TelemetryPanel({ telemetry }: { telemetry: TelemetryMessage | null }) {
  if (!telemetry) {
    return (
      <section className="card">
        <h2>Telemetry</h2>
        <p className="hint">No data.</p>
      </section>
    );
  }
  const rows: [string, string][] = [
    ["State", telemetry.state],
    ["E-stop", telemetry.estop ? "LATCHED" : "off"],
    ["Link (robot side)", telemetry.linkOk ? "ok" : "LOST"],
    ["Battery", show(telemetry.batteryV, " V")],
    ["Adhesion", `${telemetry.adhesionPct}% ${telemetry.adhesionOk ? "(ok)" : "(not ok)"}`],
    ["Motors L / R", `${telemetry.motorLeftPct}% / ${telemetry.motorRightPct}%`],
    ["Pitch / Roll", `${show(telemetry.pitchDeg, "°")} / ${show(telemetry.rollDeg, "°")}`],
    ["Uptime", `${Math.floor(telemetry.uptimeMs / 1000)} s`],
  ];
  return (
    <section className="card">
      <h2>Telemetry</h2>
      <dl className="telemetry">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
