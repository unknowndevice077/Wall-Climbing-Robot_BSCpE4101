import { useState } from "react";
import type { Robot } from "../useRobot";

/** Big, always-visible E-STOP. When latched, shows a separate Reset button. */
export function EStop({ robot }: { robot: Robot }) {
  const [notSent, setNotSent] = useState(false);
  const latched = robot.telemetry?.estop ?? true;
  const connected = robot.connection === "connected";

  const onStop = () => setNotSent(!robot.estop());

  const onReset = () => {
    if (window.confirm("Reset E-STOP? The robot will accept drive commands again.")) {
      robot.resetEstop();
    }
  };

  return (
    <footer className="estop-bar">
      {notSent && !connected && (
        <p className="estop-warning">Not connected: E-STOP not sent. Use the physical kill switch!</p>
      )}
      <button type="button" className="estop" onClick={onStop} aria-label="Emergency stop">
        E-STOP
      </button>
      {latched && connected && (
        <button type="button" className="estop-reset" onClick={onReset}>
          Reset E-STOP
        </button>
      )}
    </footer>
  );
}
