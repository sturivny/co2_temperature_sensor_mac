# Instructions for AI contributors

Read `README.md`, `docs/ARCHITECTURE.md`, `docs/PROTOCOL.md`,
`docs/HARDWARE.md`, and `VALIDATION.md` before changing this project.

## Working rules

- Keep primary documentation and pull-request descriptions in English. Preserve
  the Russian user guides under `docs/ru` and keep links and technical facts aligned.
  Documentation translation does not imply changing the existing Russian app UI.
- Never commit Wi-Fi credentials, API keys, `config.json`, SQLite databases,
  raw factory flash backups, `.tooling`, `.pio`, or local application builds.
  Credentials are entered locally and stored in device NVS; the Mac stores only
  the device API token and hostname. Never print tokens in diagnostics.
- Preserve the user's flash journal and network settings. Do not use erase-all,
  factory reset, forced calibration, or change the partition map as a routine fix.
- GPIO5 is SDA and GPIO6 is SCL for both SCD4x and the onboard OLED.
  U8g2 changes GPIO modes during initialization: end Wire before display.begin()
  so hardware I2C is reattached. Keep the recovery initialization in place.
- The received controller and physical fit, rather than seller dimensions,
  define enclosure geometry. Keep USB flush with the outside wall. Do not replace
  the v0.8 dimensions with nominal development-board dimensions.
- Retain the journal's packed 32-byte format and CRC unless a migration is designed.
  A boot ID plus uptime is not an absolute date. Never invent calendar dates for
  an unobserved unsynchronized boot.
- USB is a single-owner interface: stop this project's running Mac app before
  provisioning, flashing or running a USB diagnostic; restart it afterwards.
  Only access/flash a connected board within the user's authorized task.
- Build scripts must resolve paths relative to the checkout, never a developer's
  home directory. Do not copy the original project's toolchain into Git.
- Do not present simulated checks as physical or metrological validation.
  Update `VALIDATION.md` with exact evidence and remaining limitations.

## Checks

After setup (`python3 tools/setup.py`):

```sh
.tooling/venv/bin/python tools/check.py
PLATFORMIO_CORE_DIR="$PWD/.tooling/platformio" .tooling/venv/bin/pio run -d firmware
```

For CAD changes, install `requirements-cad.txt` into the project environment,
run all three enclosure generators, `check_mount.py`, and `check_usb_profile.py`
in `enclosure/v0.8`. Review previews and STL bounds/closed meshes. Keep the sensor
fit fixture hashes unless a deliberate geometry change is documented.

Hardware tests need the real board and local network. The default check script
must not flash hardware, change Wi-Fi settings, or open an interactive app.
