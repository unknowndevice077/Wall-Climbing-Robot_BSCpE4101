// Unit tests for the WebSocket protocol parser/writer. Run on your PC: pio test -e native
#include <ArduinoJson.h>
#include <string.h>
#include <unity.h>

#include "../../src/comms/protocol.cpp"

static const char* parse(const char* json, ClientMessage& out) {
  return protocolParseClientMessage(json, strlen(json), out);
}

void setUp() {}
void tearDown() {}

void test_parse_drive() {
  ClientMessage m;
  TEST_ASSERT_NULL(parse("{\"type\":\"drive\",\"left\":25,\"right\":-40}", m));
  TEST_ASSERT_EQUAL(ClientMessageType::DRIVE, m.type);
  TEST_ASSERT_EQUAL(25, m.leftPct);
  TEST_ASSERT_EQUAL(-40, m.rightPct);
}

void test_parse_clamps_and_rounds() {
  ClientMessage m;
  TEST_ASSERT_NULL(parse("{\"type\":\"drive\",\"left\":500,\"right\":-12.6}", m));
  TEST_ASSERT_EQUAL(100, m.leftPct);
  TEST_ASSERT_EQUAL(-13, m.rightPct);
  TEST_ASSERT_NULL(parse("{\"type\":\"adhesion\",\"power\":-5}", m));
  TEST_ASSERT_EQUAL(0, m.adhesionPct);
}

void test_parse_simple_types() {
  ClientMessage m;
  TEST_ASSERT_NULL(parse("{\"type\":\"heartbeat\"}", m));
  TEST_ASSERT_EQUAL(ClientMessageType::HEARTBEAT, m.type);
  TEST_ASSERT_NULL(parse("{\"type\":\"estop\"}", m));
  TEST_ASSERT_EQUAL(ClientMessageType::ESTOP, m.type);
  TEST_ASSERT_NULL(parse("{\"type\":\"reset_estop\"}", m));
  TEST_ASSERT_EQUAL(ClientMessageType::RESET_ESTOP, m.type);
}

void test_parse_rejects_bad_messages() {
  ClientMessage m;
  TEST_ASSERT_NOT_NULL(parse("not json", m));
  TEST_ASSERT_NOT_NULL(parse("{\"left\":1}", m));
  TEST_ASSERT_NOT_NULL(parse("{\"type\":\"fly\"}", m));
  TEST_ASSERT_NOT_NULL(parse("{\"type\":\"drive\",\"left\":\"fast\",\"right\":0}", m));
  TEST_ASSERT_NOT_NULL(parse("{\"type\":\"adhesion\"}", m));
}

void test_write_telemetry_uses_null_for_invalid_readings() {
  TelemetryData t;
  t.state = "RUNNING";
  t.estop = false;
  t.motorLeftPct = 12;
  char buffer[384];
  TEST_ASSERT_GREATER_THAN(0, protocolWriteTelemetry(t, buffer, sizeof(buffer)));

  JsonDocument doc;
  TEST_ASSERT_FALSE(deserializeJson(doc, buffer));
  TEST_ASSERT_EQUAL_STRING("telemetry", doc["type"]);
  TEST_ASSERT_EQUAL(PROTOCOL_VERSION, doc["protocol"].as<int>());
  TEST_ASSERT_EQUAL_STRING("RUNNING", doc["state"]);
  TEST_ASSERT_EQUAL(12, doc["motorLeftPct"].as<int>());
  TEST_ASSERT_TRUE(doc["batteryV"].isNull());
  TEST_ASSERT_TRUE(doc["pitchDeg"].isNull());
}

void test_write_returns_zero_when_buffer_too_small() {
  TelemetryData t;
  char buffer[16];
  TEST_ASSERT_EQUAL(0, protocolWriteTelemetry(t, buffer, sizeof(buffer)));
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_parse_drive);
  RUN_TEST(test_parse_clamps_and_rounds);
  RUN_TEST(test_parse_simple_types);
  RUN_TEST(test_parse_rejects_bad_messages);
  RUN_TEST(test_write_telemetry_uses_null_for_invalid_readings);
  RUN_TEST(test_write_returns_zero_when_buffer_too_small);
  return UNITY_END();
}
