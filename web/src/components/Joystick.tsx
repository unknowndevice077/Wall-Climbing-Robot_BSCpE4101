import { useRef, useState, type PointerEvent } from "react";

interface Props {
  disabled: boolean;
  /** left/right motor percent, -100..100. null when released. */
  onChange: (drive: { left: number; right: number } | null) => void;
}

/**
 * Touch-friendly on-screen joystick. Up = forward. Uses "tank" mixing:
 * left = forward + turn, right = forward - turn.
 */
export function Joystick({ disabled, onChange }: Props) {
  const padRef = useRef<HTMLDivElement>(null);
  const [knob, setKnob] = useState({ x: 0, y: 0 }); // -1..1

  const update = (event: PointerEvent<HTMLDivElement>) => {
    const pad = padRef.current;
    if (!pad) return;
    const rect = pad.getBoundingClientRect();
    let x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    let y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
    const length = Math.hypot(x, y);
    if (length > 1) {
      x /= length;
      y /= length;
    }
    setKnob({ x, y });
    const left = Math.max(-1, Math.min(1, y + x)) * 100;
    const right = Math.max(-1, Math.min(1, y - x)) * 100;
    onChange({ left, right });
  };

  const release = () => {
    setKnob({ x: 0, y: 0 });
    onChange(null);
  };

  return (
    <section className="card">
      <h2>Drive</h2>
      <div
        ref={padRef}
        className={`joystick ${disabled ? "joystick-disabled" : ""}`}
        onPointerDown={(e) => {
          if (disabled) return;
          e.currentTarget.setPointerCapture(e.pointerId);
          update(e);
        }}
        onPointerMove={(e) => {
          if (!disabled && e.currentTarget.hasPointerCapture(e.pointerId)) update(e);
        }}
        onPointerUp={release}
        onPointerCancel={release}
      >
        <div
          className="joystick-knob"
          style={{ left: `${50 + knob.x * 40}%`, top: `${50 - knob.y * 40}%` }}
        />
      </div>
      {disabled && <p className="hint">Driving is disabled (E-STOP or not connected).</p>}
    </section>
  );
}
