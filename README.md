# CO₂ Monitor — ESP32-C3 + SCD4x

[Русская версия](docs/ru/README.md)

CO₂, temperature and humidity readings on an OLED and in the Mac menu bar.
The device records history in its internal flash, even while the Mac is asleep.

## Repository contents

- `firmware/` — ESP32-C3 firmware.
- `macos/` — native Mac menu-bar app.
- `enclosure/v0.9/` — printable STL files, SCAD sources, generators, fit samples and previews.
- [Hardware](docs/HARDWARE.md), [architecture](docs/ARCHITECTURE.md),
  [device protocol](docs/PROTOCOL.md), [validation](VALIDATION.md).
- [AI contributor instructions](AGENTS.md).

![Enclosure](enclosure/v0.9/preview.png)

## Set up a fresh checkout

Requirements: macOS on Apple Silicon, Python 3.10+, and Xcode Command Line Tools
(`swiftc`, `clang++`, `codesign`). Generated apps, credentials and personal
measurements are excluded from Git. Run all commands from the repository root:

```bash
python3 tools/setup.py
.tooling/venv/bin/python tools/build_macos.py
.tooling/venv/bin/python tools/check.py
```

Setup installs PlatformIO and Python tools. Building the firmware additionally
downloads the pinned platform and libraries. You do not need to flash a device
again just to use it with a fresh Mac app build.

## Wiring

| Sensor pin | ESP32-C3 pin |
|---|---|
| GND | GND |
| VDD | 3V3 |
| SDA | GPIO5 |
| SCL | GPIO6 |

The onboard OLED shares GPIO5/6. The sensor address is 0x62; the OLED is 0x3C.
Use the board's pin labels rather than the orientation of a photograph.
Power the controller through USB-C from a Mac or power bank; the sensor's VDD
is connected to 3V3, not directly to USB 5 V.

## Run on a Mac

1. Connect the controller with a USB data cable.
2. If the factory screen remains after flashing, press and release RST.
3. Open `Open Monitor.command` in the repository root. CO₂ appears in the menu bar.
4. Allow about five seconds for the first measurement and one minute for the
   first history record. Unavailable or stale readings appear as “—”.
5. Use the menu for CO₂ graphs over 24 hours / 7 days, temperature graphs
   over **7 days / 24 days**, CSV export and the history folder. Temperature
   charts use the existing archive and degrees Celsius; missing history stays blank.

The app targets Apple Silicon and macOS 13+. Other macOS versions have not been
verified separately. Builds are locally ad-hoc signed. The existing app interface
and provisioning prompts are in Russian; this change translates the documentation.
Do not run the app and a USB diagnostic simultaneously: they share one port.
The original Russian launcher names remain available for compatibility.

## Use a power bank

While connected to the Mac over USB, open `Configure Wi-Fi.command`.
Enter the 2.4 GHz network name and password locally in Terminal; password input
is hidden. Restart CO2 Monitor after configuration. Provisioning needs the
checkout-local `.tooling` environment; copying only the app does not include it.

You can then power the device from a power bank and communicate over home Wi-Fi.
The Mac and sensor must be able to reach each other on the network. Recording
continues while the Mac is asleep or away. The next connection downloads retained
records without duplicates. Test your specific power bank: some turn off their
output when the load is low.

## History and timestamps

- Sensor measurements: approximately every five seconds.
- Flash records: one average of successful readings per minute.
- A 1 MiB ring stores up to 32,768 records, approximately 22 days 18 hours.
  At capacity, the oldest records are replaced in sectors of 128 records.
- The Mac archives downloaded history in SQLite beyond the device's retention period.
- Location: `~/Library/Application Support/CO2Monitor/history.sqlite`.
- A power cut loses the unfinished minute. Records have CRC checks; torn flash
  records are skipped after recovery.
- Time synchronizes through Wi-Fi/internet or a USB app connection. Before
  synchronization, the device stores a boot ID and uptime. The Mac can recover
  calendar time if it observed that same boot.
- If power is lost before synchronization and the Mac never observed that boot,
  its absolute time cannot be recovered. Measurements remain in the archive and
  CSV with an empty calendar date. Guaranteed dates after arbitrary power cuts
  require a battery-backed RTC or an available time server.
- If the ring overwrites records before download, the app reports a history gap.
  Missing measurements are never replaced with invented data.

The Wi-Fi password and API token are stored in device NVS. The Mac configuration
stores only the token and address in a local `config.json`, mode 0600. The HTTP
API uses a Bearer token without TLS on the local network; do not expose it to
the internet. A factory flash backup, if taken, stays in `.tooling/backup/`
and is not included in Git or source archives.

## Diagnostics

```bash
.tooling/venv/bin/python tools/board.py status
.tooling/venv/bin/python tools/board.py scan
.tooling/venv/bin/python tools/board.py export --output co2-history.csv
```

The scan should find decimal addresses 60 (0x3C) and 98 (0x62). If the sensor
is missing, check common ground, power and SDA/SCL. Wiring and first boot must
be checked on real hardware; successful compilation alone cannot confirm them.

## Build and flash

```bash
PLATFORMIO_CORE_DIR="$PWD/.tooling/platformio" .tooling/venv/bin/pio run -d firmware
.tooling/venv/bin/python tools/build_macos.py
.tooling/venv/bin/python tools/check.py
```

Firmware output: `firmware/.pio/build/esp32c3/firmware.bin`.
To upload, add `-t upload --upload-port /dev/cu.usbmodem…` to the PlatformIO command.
Do not use erase-all: it removes history and network settings. Any partition-map
change needs a plan to preserve existing records. The firmware does not force
calibration or change the sensor's automatic self-calibration settings.

## Edit or print the enclosure

CAD generation requires Python 3.12+ for the pinned dependencies:

```bash
.tooling/venv/bin/pip install -r requirements-cad.txt
```

Follow the [enclosure guide](enclosure/v0.9/README.md) for generators, checks and
print orientation. Ready-to-print STL files are included; printing does not
require Python or OpenSCAD.
