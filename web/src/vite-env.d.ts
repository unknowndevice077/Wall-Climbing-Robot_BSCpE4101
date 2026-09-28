/// <reference types="vite/client" />

// Firmware version from firmware/include/version.h (see vite.config.ts).
declare const __APP_VERSION__: string;

interface ImportMetaEnv {
  readonly VITE_ROBOT_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
