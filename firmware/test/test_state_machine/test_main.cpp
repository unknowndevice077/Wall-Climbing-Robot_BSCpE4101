// Unit tests for the safety logic. Run on your PC: pio test -e native
// No ESP32 needed. The state machine is plain C++, so we compile it directly here.
#include <unity.h>

#include "../../src/main/state_machine.cpp"

static ClientMessage msg(ClientMessageType type, int a = 0, int b = 0) {
  ClientMessage m;
  m.type = type;
  m.leftPct = a;
  m.rightPct = b;
  m.adhesionPct = a;
  return m;
}

// A robot that was reset and is receiving messages at t = 1000 ms.
static Commands armed() {
  Commands c;
  applyClientMessage(c, msg(ClientMessageType::RESET_ESTOP), 1000);
  return c;
}

void setUp() {}
void tearDown() {}

void test_boots_in_estop() {
  Commands c;
  TEST_ASSERT_EQUAL(RobotState::ESTOP, robotState(c, 0));
}

void test_reset_arms_the_robot() {
  Commands c = armed();
  TEST_ASSERT_EQUAL(RobotState::RUNNING, robotState(c, 1000));
}

void test_drive_moves_wheels_clamped_to_max_power() {
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 100, -100), 1010);
  Outputs o = computeOutputs(c, robotState(c, 1010), 1010);
  TEST_ASSERT_EQUAL(MAX_MOTOR_POWER_PCT, o.leftPct);
  TEST_ASSERT_EQUAL(-MAX_MOTOR_POWER_PCT, o.rightPct);
}

void test_link_loss_stops_wheels_but_keeps_adhesion() {
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::ADHESION, 80), 1000);
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 20, 20), 1000);
  const uint32_t later = 1000 + LINK_TIMEOUT_MS + 1;
  RobotState s = robotState(c, later);
  Outputs o = computeOutputs(c, s, later);
  TEST_ASSERT_EQUAL(RobotState::LINK_LOST, s);
  TEST_ASSERT_EQUAL(0, o.leftPct);
  TEST_ASSERT_EQUAL(0, o.rightPct);
  TEST_ASSERT_EQUAL(80, o.adhesionPct);
}

void test_heartbeat_keeps_link_but_stale_drive_stops_wheels() {
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 20, 20), 1000);
  const uint32_t later = 1000 + LINK_TIMEOUT_MS + 1;
  applyClientMessage(c, msg(ClientMessageType::HEARTBEAT), later);
  RobotState s = robotState(c, later);
  TEST_ASSERT_EQUAL(RobotState::RUNNING, s);
  TEST_ASSERT_EQUAL(0, computeOutputs(c, s, later).leftPct);
}

void test_estop_latches_until_reset() {
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 20, 20), 1000);
  applyClientMessage(c, msg(ClientMessageType::ESTOP), 1010);
  applyClientMessage(c, msg(ClientMessageType::HEARTBEAT), 1020);
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 20, 20), 1030);
  RobotState s = robotState(c, 1030);
  TEST_ASSERT_EQUAL(RobotState::ESTOP, s);
  TEST_ASSERT_EQUAL(0, computeOutputs(c, s, 1030).leftPct);

  applyClientMessage(c, msg(ClientMessageType::RESET_ESTOP), 1040);
  s = robotState(c, 1040);
  TEST_ASSERT_EQUAL(RobotState::RUNNING, s);
  TEST_ASSERT_EQUAL(0, computeOutputs(c, s, 1040).leftPct);  // old drive command was cleared
}

void test_estop_freezes_adhesion() {
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::ADHESION, 70), 1000);
  applyClientMessage(c, msg(ClientMessageType::ESTOP), 1010);
  const char* error = applyClientMessage(c, msg(ClientMessageType::ADHESION, 0), 1020);
  TEST_ASSERT_NOT_NULL(error);
  TEST_ASSERT_EQUAL(70, computeOutputs(c, robotState(c, 1020), 1020).adhesionPct);
}

void test_message_timestamp_from_other_core_is_not_stale() {
  // The comms core may stamp a message 1 ms "after" the control core read the clock.
  Commands c = armed();
  applyClientMessage(c, msg(ClientMessageType::DRIVE, 10, 10), 2001);
  RobotState s = robotState(c, 2000);
  TEST_ASSERT_EQUAL(RobotState::RUNNING, s);
  TEST_ASSERT_EQUAL(10, computeOutputs(c, s, 2000).leftPct);
}

int main() {
  UNITY_BEGIN();
  RUN_TEST(test_boots_in_estop);
  RUN_TEST(test_reset_arms_the_robot);
  RUN_TEST(test_drive_moves_wheels_clamped_to_max_power);
  RUN_TEST(test_link_loss_stops_wheels_but_keeps_adhesion);
  RUN_TEST(test_heartbeat_keeps_link_but_stale_drive_stops_wheels);
  RUN_TEST(test_estop_latches_until_reset);
  RUN_TEST(test_estop_freezes_adhesion);
  RUN_TEST(test_message_timestamp_from_other_core_is_not_stale);
  return UNITY_END();
}
