// WebSocket connection to the robot: auto-reconnect, heartbeat, and commands.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ClientMessage,
  type TelemetryMessage,
  clampPct,
  parseRobotMessage,
  SEND_INTERVAL_MS,
} from "./protocol";

/** VITE_ROBOT_WS_URL (for `npm run dev` on a laptop), else the robot that served this page. */
function robotUrl(): string {
  const fromEnv = import.meta.env.VITE_ROBOT_WS_URL;
  if (fromEnv) return fromEnv;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws`;
}

/** No telemetry for this long = treat the connection as dead and reconnect. */
const TELEMETRY_TIMEOUT_MS = 1000;
const RECONNECT_MIN_MS = 500;
const RECONNECT_MAX_MS = 3000;

export type Connection = "connecting" | "connected" | "disconnected";

export interface Robot {
  connection: Connection;
  url: string;
  telemetry: TelemetryMessage | null;
  firmwareVersion: string | null;
  protocolVersion: number | null;
  lastError: string | null;
  /** Joystick position, -100..100 each. null = joystick released. */
  setDrive: (drive: { left: number; right: number } | null) => void;
  setAdhesion: (power: number) => void;
  estop: () => boolean;
  resetEstop: () => void;
}

export function useRobot(): Robot {
  const url = robotUrl();
  const [connection, setConnection] = useState<Connection>("connecting");
  const [telemetry, setTelemetry] = useState<TelemetryMessage | null>(null);
  const [firmwareVersion, setFirmwareVersion] = useState<string | null>(null);
  const [protocolVersion, setProtocolVersion] = useState<number | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const driveRef = useRef<{ left: number; right: number } | null>(null);
  const lastTelemetryAtRef = useRef(0);

  const send = useCallback((message: ClientMessage): boolean => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(message));
    return true;
  }, []);

  // Connect, and reconnect with a growing delay when the connection drops.
  useEffect(() => {
    let stopped = false;
    let retryDelay = RECONNECT_MIN_MS;
    let retryTimer: number | undefined;

    const connect = () => {
      setConnection("connecting");
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        retryDelay = RECONNECT_MIN_MS;
        lastTelemetryAtRef.current = Date.now();
        setConnection("connected");
      };
      socket.onmessage = (event) => {
        const message = parseRobotMessage(String(event.data));
        if (!message) return;
        if (message.type === "hello") {
          setFirmwareVersion(message.firmware);
          setProtocolVersion(message.protocol);
        } else if (message.type === "telemetry") {
          lastTelemetryAtRef.current = Date.now();
          setTelemetry(message);
          setFirmwareVersion(message.firmware);
          setProtocolVersion(message.protocol);
        } else {
          setLastError(message.message);
        }
      };
      socket.onclose = () => {
        if (socketRef.current === socket) socketRef.current = null;
        setConnection("disconnected");
        setTelemetry(null);
        if (!stopped) {
          retryTimer = window.setTimeout(connect, retryDelay);
          retryDelay = Math.min(retryDelay * 2, RECONNECT_MAX_MS);
        }
      };
      socket.onerror = () => socket.close();
    };

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      socketRef.current?.close();
    };
  }, [url]);

  // Every SEND_INTERVAL_MS: send the joystick position while driving, otherwise a heartbeat.
  // Also drop connections that stopped sending telemetry (e.g. walked out of WiFi range).
  useEffect(() => {
    const timer = window.setInterval(() => {
      const drive = driveRef.current;
      send(drive ? { type: "drive", ...drive } : { type: "heartbeat" });

      const socket = socketRef.current;
      if (
        socket?.readyState === WebSocket.OPEN &&
        Date.now() - lastTelemetryAtRef.current > TELEMETRY_TIMEOUT_MS
      ) {
        socket.close();
      }
    }, SEND_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [send]);

  const setDrive = useCallback(
    (drive: { left: number; right: number } | null) => {
      if (drive === null) {
        // Released: tell the robot to stop right away, then go back to heartbeats.
        if (driveRef.current) send({ type: "drive", left: 0, right: 0 });
        driveRef.current = null;
        return;
      }
      driveRef.current = {
        left: clampPct(drive.left, -100, 100),
        right: clampPct(drive.right, -100, 100),
      };
    },
    [send],
  );

  const setAdhesion = useCallback(
    (power: number) => {
      send({ type: "adhesion", power: clampPct(power, 0, 100) });
    },
    [send],
  );

  const estop = useCallback(() => {
    driveRef.current = null;
    return send({ type: "estop" });
  }, [send]);

  const resetEstop = useCallback(() => {
    driveRef.current = null;
    send({ type: "reset_estop" });
  }, [send]);

  return {
    connection,
    url,
    telemetry,
    firmwareVersion,
    protocolVersion,
    lastError,
    setDrive,
    setAdhesion,
    estop,
    resetEstop,
  };
}
