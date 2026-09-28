# Tests

Tests here run **on your PC**, not on the ESP32. They check plain C++ logic (no `Arduino.h`):
the safety state machine (`test_state_machine/`) and the WebSocket protocol parser (`test_protocol/`),
so bugs are caught before anything touches the robot.

Run them from the `firmware/` folder:
```bash
pio test -e native
```

- CI runs them automatically on every PR, so you don't *have* to run them locally.
- Locally you need a C++ compiler (`gcc`/`g++`) on your PATH.
  - Linux/macOS: usually already installed.
  - Windows: easiest is to let PlatformIO download MinGW, then add it to PATH for the current terminal:
    ```bash
    pio pkg install -g -t platformio/toolchain-gccmingw32
    ```
    Git Bash: `export PATH="$HOME/.platformio/packages/toolchain-gccmingw32/bin:$PATH"`
    PowerShell: `$env:PATH = "$HOME\.platformio\packages\toolchain-gccmingw32\bin;$env:PATH"`

## Adding a test
1. Create a folder `test/test_<name>/` with a `test_main.cpp` (copy `test_state_machine/` as a template).
2. Only test code that doesn't need `Arduino.h`. Move logic you want to test into a plain C++ function.
3. Each test is a `void test_...()` function using `TEST_ASSERT_...`, listed in `main()` with `RUN_TEST(...)`.
