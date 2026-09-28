import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Use the firmware's version string, so UI and firmware built from the same commit match.
const versionHeader = readFileSync(
  fileURLToPath(new URL("../firmware/include/version.h", import.meta.url)),
  "utf8",
);
const match = versionHeader.match(/FIRMWARE_VERSION\s*=\s*"([^"]+)"/);
if (!match) throw new Error("Could not find FIRMWARE_VERSION in firmware/include/version.h");

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(match[1]),
  },
  build: {
    // Small output for the ESP32's flash. No source maps on the robot.
    sourcemap: false,
    assetsInlineLimit: 8192,
  },
});
