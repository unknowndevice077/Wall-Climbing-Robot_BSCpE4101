#!/usr/bin/env node
// =============================================================================
// build-web.mjs — build the web UI and put it into firmware/data for LittleFS.
//
//   node scripts/build-web.mjs        (works on Windows, macOS and Linux)
//
// Steps:
//   1. check the protocol version matches in firmware and web
//   2. `npm run build` in web/  (TypeScript check + Vite build -> web/dist)
//   3. gzip every file from web/dist into firmware/data/<name>.gz
//
// Then upload with PlatformIO: "Upload Filesystem Image" (pio run -t uploadfs).
// firmware/data is GENERATED: never edit it by hand, it is git-ignored.
// =============================================================================
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const webDir = join(root, "web");
const distDir = join(webDir, "dist");
const dataDir = join(root, "firmware", "data");

// LittleFS partition on a 4 MB ESP32 with the default partition table is ~1.3 MB.
const WARN_TOTAL_BYTES = 1_000_000;

function fail(message) {
  console.error(`\nbuild-web: ERROR: ${message}`);
  process.exit(1);
}

// 1. Protocol version must match on both sides.
function readVersion(file, pattern) {
  const match = readFileSync(join(root, file), "utf8").match(pattern);
  if (!match) fail(`could not find PROTOCOL_VERSION in ${file}`);
  return Number(match[1]);
}
const firmwareProtocol = readVersion("firmware/include/protocol.h", /PROTOCOL_VERSION\s*=\s*(\d+)/);
const webProtocol = readVersion("web/src/protocol.ts", /PROTOCOL_VERSION\s*=\s*(\d+)/);
if (firmwareProtocol !== webProtocol) {
  fail(
    `PROTOCOL_VERSION mismatch: firmware/include/protocol.h = ${firmwareProtocol}, ` +
      `web/src/protocol.ts = ${webProtocol}. Update both (and docs/protocol.md).`,
  );
}
console.log(`build-web: protocol version ${webProtocol} matches`);

// 2. Build the web app.
if (!existsSync(join(webDir, "node_modules"))) {
  fail("web/node_modules is missing. Run `npm ci` inside the web/ folder first.");
}
const build = spawnSync("npm", ["run", "build"], { cwd: webDir, stdio: "inherit", shell: true });
if (build.status !== 0) fail("web build failed (see errors above)");

// 3. Gzip everything into firmware/data.
function listFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? listFiles(path) : [path];
  });
}

rmSync(dataDir, { recursive: true, force: true });
mkdirSync(dataDir, { recursive: true });

let total = 0;
for (const file of listFiles(distDir)) {
  const name = relative(distDir, file).split("\\").join("/");
  const gz = gzipSync(readFileSync(file), { level: 9 });
  const target = join(dataDir, `${name}.gz`);
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, gz);
  total += gz.length;
  console.log(`  ${name}.gz  ${(gz.length / 1024).toFixed(1)} KB`);
}
console.log(`build-web: wrote ${(total / 1024).toFixed(1)} KB to firmware/data`);
if (total > WARN_TOTAL_BYTES) {
  console.warn("build-web: WARNING: the web UI is getting big for the ESP32's LittleFS partition.");
}
console.log('Next: PlatformIO "Upload Filesystem Image" (pio run -t uploadfs), then upload the firmware.');
