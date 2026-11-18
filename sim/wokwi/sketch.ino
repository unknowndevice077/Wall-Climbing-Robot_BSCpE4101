#define WOKWI  // serial control only, no Wi-Fi AP in Wokwi
// Wall climbing robot - ESP32 firmware
// Same control idea as sim/climb.py: pick a force for each prop in the world frame
// (X = toward wall, Z = up), then turn it into a hoop angle using the IMU pitch.
//
// Control: join Wi-Fi "WallClimber" (pass climb1234) and open http://192.168.4.1
//          or type serial commands at 115200 (type "h" for help) - used in Wokwi.
// Libraries: ESP32Servo (Kevin Harrington). Board: "ESP32 Dev Module".

#include <Arduino.h>
#include <Wire.h>
#include <ESP32Servo.h>
#ifndef WOKWI
#include <WiFi.h>
#include <WebServer.h>
#endif

// ---------- pins ----------
const int PIN_ESC_F = 25, PIN_ESC_R = 26;
const int PIN_PITCH_F = 18, PIN_ROLL_F = 19, PIN_PITCH_R = 32, PIN_ROLL_R = 33;
const int PIN_BUMPER = 27;   // front microswitch to GND
const int PIN_VBAT = 34;     // 100k / 27k divider
const int PIN_LED = 2;
// MPU6050 on I2C: SDA 21, SCL 22

// ---------- robot numbers (tune after weighing + thrust test) ----------
const float MASS = 0.95;        // kg, weigh the real robot
const float G = 9.81;
const float TMAX = 6.6;         // N per prop at 11.1 V (measure it, see docs/BUILD.md)
const float PHI_MIN = -40, PHI_MAX = 140;   // hoop angle range, deg. 90 = prop pushes forward
// per-servo trim: servo degrees where the hoop is at PHI_MIN. flip if the servo is mounted mirrored
float trimF = 0, trimR = 0;
bool flipF = false, flipR = true;
const float VDIV = (100.0 + 27.0) / 27.0;

Servo escF, escR, pitchF, pitchR, rollF, rollR;

enum Mode { DISARMED, DRIVE, CLIMB };
Mode mode = DISARMED;
float stick = 0, steer = 0;     // -1..1 from phone / serial
unsigned long lastCmd = 0;
float pitchDeg = 0;             // 0 flat, 90 nose up on the wall
float vbat = 0;
const char *phase = "idle";

// ---------- IMU (raw MPU6050, no library) ----------
void imuInit() {
  Wire.begin(21, 22);
  Wire.beginTransmission(0x68); Wire.write(0x6B); Wire.write(0); Wire.endTransmission();  // wake
  Wire.beginTransmission(0x68); Wire.write(0x1B); Wire.write(0x08); Wire.endTransmission(); // gyro +-500 dps
}

void imuRead(float dt) {
  Wire.beginTransmission(0x68); Wire.write(0x3B); Wire.endTransmission(false);
  if (Wire.requestFrom(0x68, 14) != 14) return;
  int16_t v[7];
  for (int i = 0; i < 7; i++) v[i] = (Wire.read() << 8) | Wire.read();
  float ax = v[0], az = v[2], gy = v[5] / 65.5;           // deg/s
  float accPitch = atan2(ax, az) * 180 / PI;
  // nose-up is a negative rotation about Y (Y points left)
  pitchDeg = 0.98 * (pitchDeg - gy * dt) + 0.02 * accPitch;
}

// ---------- outputs ----------
void writeHoop(Servo &s, float phi, float trim, bool flip) {
  phi = constrain(phi, PHI_MIN, PHI_MAX);
  float deg = phi - PHI_MIN + trim;
  if (flip) deg = 180 - deg;
  s.write((int)constrain(deg, 0, 180));
}

void writeEsc(Servo &e, float thrustN) {
  if (mode == DISARMED || thrustN < 0.05) { e.writeMicroseconds(1000); return; }
  float thr = sqrt(constrain(thrustN / TMAX, 0, 1));    // thrust ~ rpm^2 ~ throttle^2
  e.writeMicroseconds(1050 + (int)(900 * thr));
}

// wanted world force (Fx toward wall, Fz up) -> hoop angle + thrust
void setProp(float fx, float fz, Servo &hoop, Servo &esc, float trim, bool flip) {
  float p = pitchDeg * PI / 180;
  float bx = fx * cos(p) + fz * sin(p);
  float bz = -fx * sin(p) + fz * cos(p);
  float phi = atan2(bx, bz) * 180 / PI;
  float mag = sqrt(bx * bx + bz * bz);
  writeHoop(hoop, phi, trim, flip);
  writeEsc(esc, min(mag, TMAX));
}

float lerpf(float a, float b, float t) { return a + (b - a) * t; }

void control() {
  float halfW = 0.5 * MASS * G;
  float fFx = 0, fFz = 0, fRx = 0, fRz = 0;
  bool bumper = digitalRead(PIN_BUMPER) == LOW;

  if (mode == DRIVE) {
    phase = "drive";
    fFx = fRx = 1.6 * stick;                   // negative = reverse (hoop tips back to -40 deg)
    fFz = fRz = stick < 0 ? 1.0 : 0;
  } else if (mode == CLIMB) {
    if (pitchDeg < 15 && !bumper) {            // still rolling up to the wall
      phase = "approach";
      fFx = fRx = 1.6;
    } else if (pitchDeg < 80) {                // nose-up onto the wall
      phase = "transition";
      float w = constrain(pitchDeg / 80, 0, 1);
      float up = halfW * 1.05;
      fFx = lerpf(1.0, 4.2, w); fFz = lerpf(7.0, up, w);
      fRx = lerpf(2.0, 2.6, w); fRz = lerpf(1.5, up, w);
    } else {                                   // on the wall: stick = climb / hold / descend
      phase = stick > 0.05 ? "climb" : stick < -0.05 ? "descend" : "hold";
      float up = halfW * (1.03 + 0.12 * stick);
      fFx = 4.2; fFz = up;                     // top hoop pushes harder: stops the top wheels peeling
      fRx = 2.6; fRz = up;
    }
  } else phase = "idle";

  setProp(fFx, fFz, pitchF, escF, trimF, flipF);
  setProp(fRx, fRz, pitchR, escR, trimR, flipR);
  // steering: tilt the motor arms opposite ways -> yaw
  rollF.write(90 + (int)(25 * steer));
  rollR.write(90 - (int)(25 * steer));
}

// ---------- commands (shared by web + serial) ----------
void command(char c, float a, float b) {
  lastCmd = millis();
  if (c == 'a') mode = DRIVE;
  else if (c == 'c') mode = CLIMB;
  else if (c == 'x') { mode = DISARMED; stick = steer = 0; }
  else if (c == 's') { stick = constrain(a, -1, 1); steer = constrain(b, -1, 1); }
}

void serialInput() {
  static String line;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch != '\n' && ch != '\r') { line += ch; continue; }
    if (!line.length()) continue;
    float a = 0, b = 0;
    sscanf(line.c_str() + 1, "%f %f", &a, &b);
    if (line[0] == 'h') Serial.println("a=arm drive  c=climb mode  x=STOP  s <stick -1..1> <steer -1..1>  e.g. 's 0.5 0'");
    else command(line[0], a, b);
    line = "";
  }
}

#ifndef WOKWI
WebServer web(80);
const char PAGE[] PROGMEM = R"HTML(<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{font-family:sans-serif;margin:16px;background:#111;color:#eee}button{font-size:20px;padding:14px;margin:4px;border:0;border-radius:8px}
input{width:100%;height:40px}#x{background:#c33;color:#fff;width:100%;font-size:28px}</style>
<h2>Wall Climber</h2><div id=st>...</div>
<button onclick="c('a')">Drive</button><button onclick="c('c')">Climb</button>
<p>Throttle / climb<input id=s type=range min=-100 max=100 value=0></p>
<p>Steer<input id=t type=range min=-100 max=100 value=0></p>
<button onclick="z()">Center sticks</button><button id=x onclick="c('x')">STOP</button>
<script>
function c(m){fetch('/cmd?c='+m)}
function z(){s.value=0;t.value=0}
setInterval(()=>fetch('/cmd?c=s&a='+s.value/100+'&b='+t.value/100).then(r=>r.text()).then(x=>st.textContent=x).catch(()=>st.textContent='NO LINK'),100)
</script>)HTML";

void webInit() {
  WiFi.softAP("WallClimber", "climb1234");
  web.on("/", [] { web.send_P(200, "text/html", PAGE); });
  web.on("/cmd", [] {
    String c = web.arg("c");
    if (c.length()) command(c[0], web.arg("a").toFloat(), web.arg("b").toFloat());
    char buf[96];
    snprintf(buf, sizeof buf, "%s | %s | pitch %.0f | %.1f V", mode == DISARMED ? "STOPPED" : mode == DRIVE ? "DRIVE" : "CLIMB", phase, pitchDeg, vbat);
    web.send(200, "text/plain", buf);
  });
  web.begin();
}
#endif

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUMPER, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  for (int i = 0; i < 4; i++) ESP32PWM::allocateTimer(i);
  escF.setPeriodHertz(50); escR.setPeriodHertz(50);
  escF.attach(PIN_ESC_F, 1000, 2000); escR.attach(PIN_ESC_R, 1000, 2000);
  pitchF.attach(PIN_PITCH_F, 500, 2500); pitchR.attach(PIN_PITCH_R, 500, 2500);
  rollF.attach(PIN_ROLL_F, 500, 2500); rollR.attach(PIN_ROLL_R, 500, 2500);
  escF.writeMicroseconds(1000); escR.writeMicroseconds(1000);   // ESCs arm on low throttle
  imuInit();
#ifndef WOKWI
  webInit();
#endif
  delay(3000);
  Serial.println("ready - type h for help");
}

void loop() {
  static unsigned long t0 = micros(), lastPrint = 0;
  unsigned long now = micros();
  float dt = (now - t0) / 1e6; t0 = now;
  imuRead(dt);
  vbat = analogReadMilliVolts(PIN_VBAT) / 1000.0 * VDIV;
  serialInput();
#ifndef WOKWI
  web.handleClient();
#endif
  // lost link: drive mode stops, on the wall it holds for 5 s then cuts (keep a mat under the wall!)
#ifndef WOKWI
  unsigned long quiet = millis() - lastCmd;
  if (mode == DRIVE && quiet > 600) mode = DISARMED;
  if (mode == CLIMB && quiet > 600) stick = 0;
  if (mode == CLIMB && quiet > 5600) mode = DISARMED;
#endif
  if (vbat > 6 && vbat < 9.9 && mode != CLIMB) mode = DISARMED;   // 3.3 V/cell
  control();
  digitalWrite(PIN_LED, mode != DISARMED);
  if (millis() - lastPrint > 500) {
    lastPrint = millis();
    Serial.printf("mode=%d phase=%s pitch=%.1f vbat=%.2f stick=%.2f\n", mode, phase, pitchDeg, vbat, stick);
  }
  delay(5);
}
