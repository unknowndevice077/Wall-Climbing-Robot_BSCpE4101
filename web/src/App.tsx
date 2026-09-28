import { AdhesionControl } from "./components/AdhesionControl";
import { ConnectionStatus } from "./components/ConnectionStatus";
import { EStop } from "./components/EStop";
import { Joystick } from "./components/Joystick";
import { TelemetryPanel } from "./components/TelemetryPanel";
import { useRobot } from "./useRobot";

export function App() {
  const robot = useRobot();
  const connected = robot.connection === "connected";
  const estopLatched = robot.telemetry?.estop ?? true;
  const locked = !connected || estopLatched;

  return (
    <div className={`app ${connected ? "" : "app-disconnected"}`}>
      <ConnectionStatus robot={robot} />
      <main>
        {robot.lastError && <p className="error">Robot says: {robot.lastError}</p>}
        <Joystick disabled={locked} onChange={robot.setDrive} />
        <AdhesionControl
          disabled={locked}
          actualPct={robot.telemetry?.adhesionPct ?? null}
          onSet={robot.setAdhesion}
        />
        <TelemetryPanel telemetry={robot.telemetry} />
      </main>
      <EStop robot={robot} />
    </div>
  );
}
