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

## Enclosure v0.9 — 27 October 2026

User feedback: rear controller axial stop fractured after use. v0.9 adds a wider
wall, floor-overlapping foot and two gussets; retains the fitted contact datum.
The divider slot is now 8 mm wide and open from the top for prewired boards.
The lid and screw coupon now have straight Ø2.4 mm holes and flat external seats
for M2 socket heads, with M2×10 measured under the head.

All three v0.9 generators, mount and USB-profile checks, and revision checks
passed. All eight serialized STLs are closed, consistently wound single solids.
PCB/component envelopes, insertion, lid removal, wire-drop clearance, flat seats,
unchanged sensor fixtures and unchanged USB placement passed digital checks.
The only removed base material is inside the new wire slot. Source v0.8 is
preserved. Preview images were inspected. Physical strength, fatigue, screw fit
and actual wiring installation for v0.9 remain unverified. No hardware was flashed.

## Temperature charts and app update — 28 October 2026

- App version 0.2.0 adds temperature charts for 7 days and 24 days, preserving
  the existing CO₂ chart periods and using the archived temperature column.
- C++ journal checks and Swift app build/signature/self-tests passed. New checks
  cover metric selection, 7/24-day filtering, exclusion of future/older records,
  subzero temperatures, constant-temperature axes and CO₂ regression.
- Both temperature views were rendered from a temporary snapshot of the real
  SQLite archive; the 24-day image was visually inspected. Snapshot and images
  are local ignored build outputs and are not included in Git.
- The running app bundle was backed up, replaced with 0.2.0, signature/hash
  checked, and relaunched. History was backed up and preserved without migration.
- v0.9 mount, USB-profile and revision checks passed again before publication.
  Its physical strength and wiring installation still require a print trial.

## Corrected temperature periods — app 0.2.1, 28 October 2026

The user corrected the requested period from 24 days to **24 hours**. Temperature
now offers the same periods as CO₂: 24 hours and 7 days. The original 0.2.0 entry
above is historical evidence, not the current behavior. Regression fixtures now
distinguish a reading six hours old from one six days old and exclude records
older than a week or dated in the future. Build, signing and host checks passed.
