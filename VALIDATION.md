# Validation — 16 October 2026

[Русская версия](docs/ru/VALIDATION.md)

## Hardware and software evidence

- Firmware built for ESP32-C3 with 4 MiB flash, Arduino ESP32 2.0.17 and
  PlatformIO espressif32 6.12.0.
- The original 4 MiB factory flash was backed up locally before the first upload
  in `.tooling/backup`; it is excluded from Git.
- Firmware upload to the physical board completed with hash verification.
- The sensor responded at 0x62 and the OLED was found at 0x3C on GPIO5/6.
- Real readings were received, for example 418 ppm / 25.18 °C / 41.54% RH.
  This verifies data acquisition, not metrological accuracy.
- The device journal reported `healthy=true`, `capacity=32768`. Its first record
  was read and saved through the native Mac USB transport (`--usb-check`).
- C++ host checks passed: sensor/journal CRC reference vectors, 32 interrupted
  write positions, 1,800 writes through ring wrap, reboot recovery, pagination
  and corrupted records.
- Native Swift checks passed: compilation, local signing, SQLite storage,
  duplicate import, time recovery, gap accounting and CSV export. Reading real
  device status and history through the app's USB transport also passed.
- The initial upload workflow needed a physical RST press. The latest upload
  also successfully restarted automatically using the watchdog.
- Firmware 0.1.1 fixes hardware I²C recovery after U8g2 configures GPIO modes.
  After the update, `sensor_started=true`, `oled_found=true`, and `error` was empty.
  Existing history survived and grew from one to two records.
- The user confirmed that readings were visible on the OLED.
- Wi-Fi association was confirmed. Authenticated `/api/status` and `/api/history`
  were read from the Mac using mDNS; real readings and history arrived over the
  network, and `unix_s` was populated.
- Power-bank operation after disconnecting Mac USB has not yet been verified.

## Repository handoff

Checks run from the new checkout on 16 October 2026:

- `tools/check.py`: Python syntax, journal C++ tests, Mac app build/signing and
  SQLite/CSV self-test — PASS.
- Firmware build with pinned dependencies — PASS: 42,436 bytes RAM and 857,652
  bytes flash as reported by PlatformIO.
- `check_mount.py` and `check_usb_profile.py` — PASS. Mount checks now use saved
  sensor fixture hashes and do not require the old v0.7 directory.
- Eight STL files: closed meshes, consistent winding, one connected body each.
- Local documentation links were checked.
- Known access keys, the Wi-Fi password, Mac configuration, SQLite history and
  factory flash were excluded. Deliverables were scanned for known credentials
  without printing their values.
- The device was not reflashed during the repository transfer. Hardware evidence
  above refers to the earlier physical tests, not simulated repository checks.

## Remaining limitations

No reference-gas calibration, temperature-offset calibration or accuracy testing
inside the fully assembled enclosure has been performed. Fit confirmation and
mesh validation do not establish sensor accuracy, fastener lifetime, snap fatigue,
or compatibility with every printer, cable and power bank.
