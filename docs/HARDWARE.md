# Hardware and enclosure

[Русская версия](ru/HARDWARE.md)

## Wiring

Verified wiring: **GND → GND, VDD → 3V3, SDA → GPIO5, SCL → GPIO6**.
Wires are soldered directly to the pads without headers. OLED and sensor share
the bus: OLED at 0x3C, sensor at 0x62. Power the controller through USB-C.
GPIO numbers are not physical pin positions; do not infer wiring from a rotated photo.

The order specified an SCD40 module; later seller information described SCD41.
The firmware uses the shared SCD4x periodic measurement mode. The exact variant
and specified accuracy of the individual received sensor were not independently verified.

During bring-up, U8g2 initialization interfered with an already-running Wire bus.
Firmware 0.1.1 fixes this by calling Wire.end() before display.begin(), allowing
hardware I²C to reattach to the pins. If the OLED does not respond during startup,
it is probed again after five seconds.

## Measured dimensions

| Part | Dimension |
|---|---|
| Controller PCB | 24.8 × 20.6 mm |
| Controller corners | approximately 1 × 1 mm chamfers at 45° |
| Sensor PCB | 22.2 × 13 mm |
| PCB thickness | 1.5 mm |
| Overall sensor height | 8 mm |
| Measured overall controller height | 4 mm |
| USB-C protrusion beyond PCB | 2 mm |
| USB-C metal shell | 9 × 3 mm |
| Shell bottom above PCB bottom | 1.1 mm |
| Screws for v0.9 | M2 × 10 mm under the head, socket head outside the lid |

Enclosure v0.9: **78 × 40 × 17 mm**, R3 corners, R0.6 edges, 2 mm walls/floor/lid.
The USB-C opening is a 9.6 × 3.6 mm capsule with R1.8 ends. The connector is
nominally flush with the outside wall. Supports contact straight PCB edges,
not the chamfered corners. The lid uses straight Ø2.4 mm holes with flat external seats for M2 socket
heads. M2×10 length is measured under the head; no countersink is present. Snap tabs are included on fit samples; the full enclosure
uses supports and lid retention features. There is no internal battery or SD card.

The user confirmed that the final fit sample fitted correctly and started
printing the enclosure. Closed-enclosure temperature accuracy, all cable shapes,
snap durability and the specific power bank have not been comprehensively tested.

Print files and detailed instructions: [enclosure/v0.8](../enclosure/v0.9/README.md).

## Interpreting CO₂

The device measures CO₂, not oxygen. For household ventilation, a practical guide
is below 1,000 ppm: good; 1,000–1,500: consider airing; 1,500–2,000: inadequate
ventilation; above 2,000: increase ventilation. These are ventilation indicators,
not poisoning thresholds or a complete assessment of air contaminants.
Follow trends and place the monitor over 0.5 m from faces and away from open windows.

Sources: [UBA](https://www.umweltbundesamt.de/sites/default/files/medien/pdfs/kohlendioxid_2008.pdf),
[HSE](https://www.hse.gov.uk/ventilation/using-co2-monitors.htm).
Sensor protocol: [Sensirion SCD4x datasheet](https://admin.sensirion.com/media/documents/48C4B7FB/64C134E7/Sensirion_SCD4x_Datasheet.pdf).
