import { useEffect, useState } from "react";

interface Props {
  disabled: boolean;
  /** Power the robot reports it is applying, 0..100. */
  actualPct: number | null;
  onSet: (power: number) => void;
}

/** Adhesion power slider. Turning it to 0 asks for confirmation (robot could fall). */
export function AdhesionControl({ disabled, actualPct, onSet }: Props) {
  const [value, setValue] = useState(actualPct ?? 0);

  // Follow the robot's value when it changes on its own (e.g. after reconnect).
  useEffect(() => {
    if (actualPct !== null) setValue(actualPct);
  }, [actualPct]);

  const commit = (power: number) => {
    if (power === 0 && (actualPct ?? 0) > 0) {
      const ok = window.confirm(
        "Turn adhesion OFF?\nOnly do this if the robot is being held or is off the wall.",
      );
      if (!ok) {
        setValue(actualPct ?? 0);
        return;
      }
    }
    onSet(power);
  };

  return (
    <section className="card">
      <h2>
        Adhesion <span className="value">{value}%</span>
      </h2>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(Number(e.target.value))}
        onPointerUp={(e) => commit(Number(e.currentTarget.value))}
        onKeyUp={(e) => commit(Number(e.currentTarget.value))}
        aria-label="Adhesion power"
      />
      <p className="hint">
        Robot: {actualPct ?? "?"}%. {disabled && "Locked while E-STOP is active or not connected."}
      </p>
    </section>
  );
}
