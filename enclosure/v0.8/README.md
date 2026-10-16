# CO₂ enclosure v0.8 — flush USB and straight-edge PCB supports

[Русская версия](../../docs/ru/ENCLOSURE.md) · [Project guide](../../README.md)

## Geometry after the physical fit test

The sensor sample fitted correctly. The earlier controller sample supported
the corners poorly and recessed the USB connector. The final measured controller
is **24.8 × 20.6 mm**. Its corners are modeled as approximately 1 × 1 mm
45° chamfers; the actual rounded corner radius was not measured.

In v0.8:

- Four lower supports contact the straight long PCB edges. Each starts 2 mm
  from an end, is 2 mm long and overlaps the PCB by 0.8 mm. Corners are not used
  as support points.
- Stops in front of the USB edge were removed. The PCB's USB-side edge sits
  against the inside wall. A separate centered rear stop has 0.15 mm clearance.
- Both the inside wall and PCB edge are at x=76 mm. The connector protrudes
  2 mm and ends at the outside wall, x=78 mm: **nominal USB recess is zero**.
  The fit sample uses the same geometry.
- Lid retention features and the OLED opening move with the controller. The
  fit sample retains its side snap tabs.
- Sensor mounts are unchanged. Both sensor sample STLs are byte-identical to
  v0.7; reprinting them is unnecessary if that version already fitted.
- Lid and posts accommodate **2 × 10 mm countersunk screws, head Ø4.6 mm**.

The user subsequently confirmed that the final sample fitted correctly and
started printing the full enclosure. See [validation](../../VALIDATION.md) for
separate electrical checks and remaining limits.

## Fit samples

Start with **`fit_esp32_snaps.stl`**, the controller sample with snap tabs and a
USB wall. Its bounds are 28.8 × 24.6 × 15 mm. Use v0.8 rather than an earlier sample.

Point USB toward the wall, gently spread the tabs and lower the PCB onto its
four supports. The PCB's front edge should reach the inside USB wall. Releasing
the tabs should retain the PCB without loading the glass or connector. Check
that supports do not land on solder or components: their exact shapes were
not fully reconstructed from photographs.

Connect the actual cable and check full insertion. If plastic obstructs it,
do not bend the board or force the plug. To remove the PCB, spread the tabs
and lift by the PCB edges. `fit_esp32.stl` has the same supports and wall
without the side snap tabs.

## Enclosure dimensions

Assembled bounds: **78 × 40 × 17 mm**. Corners R3, outer horizontal edges R0.6.
The floor is 2 mm thick, PCB bottom is at z=5 mm, PCB thickness is 1.5 mm and
the lid skin is 2 mm thick. There is 2 mm clearance above the modeled sensor.

The USB-C opening is a **9.6 × 3.6 mm capsule, end radius R1.8**. It accommodates
the measured 9 × 3 mm shell with 0.3 mm contour clearance. The metal shell's
bottom is 1.1 mm above the PCB bottom: shell z=6.1–9.1 mm, opening z=5.8–9.4 mm.
The profile was compared with USB-IF Figure 3-1; the connector's exact catalog
part is unknown. Vertical placement was preserved while the PCB depth changed.

Sensor PCB: 22.2 × 13 mm, overall height 8 mm, metal body 8 × 8 mm. Its position
and dimensions are unchanged. The controller glass is modeled as 12 × 12 mm
using the user's earlier measurements. Wires are directly soldered; headers,
an internal battery and SD card are not included. Power comes from USB, with
history in ESP32 flash and download to the Mac. Firmware and app are in the
repository root.

## Screws and countersinks

The design assumes 2 mm screws with **10 mm overall length including the
countersunk head**, head diameter 4.6 mm. The cone angle is assumed to be
**90°**, not measured. Lid countersinks are Ø4.8 mm with Ø2.4 mm through holes.
A 1.2 mm cone depth leaves 0.8 mm of lid material around the through hole.

Pilot holes in posts are Ø1.7 mm, 10 mm deep. Under these assumptions the head
sits about 0.1 mm below the lid and the screw tip has about 1.9 mm clearance
to the pilot-hole bottom.

Before assembly, print **`screw_test_base.stl` and `screw_test_cap.stl`**. Fit the
small cap to the block and insert one real screw by hand. Check seating,
clamping, clearance and cracking. No electronics are needed. If the measured
10 mm excludes the head or its angle differs from 90°, revise the geometry.
The Ø1.7 mm pilot assumes threading directly into plastic; the thread type
was not identified and no nuts or inserts are modeled. Do not force a screw
that encounters substantial resistance.

## Printing and assembly

Use millimeters and 100% scale. Print the base and samples bottom-down.
The full lid STL is already inverted with its flat outside face on the bed.
Print the screw-test cap with its flat lower face on the bed.

Starting settings: 0.4 mm nozzle, 0.2 mm layers, three perimeters. PETG is
preferred for flexible snap tabs; PLA can be used for a careful initial fit
check. Do not fill the flexible tab slots with support material. Inspect thin
walls, chamfers and the USB bridge in the slicer; tab slots must remain free
of first-layer fusion.

Side snap tabs are **only on fit samples**. In the full enclosure, lower supports
work with lid retention features, also positioned over straight PCB edges.
Keep wires and solder clear of supports and retention tips.

## Files

- `fit_esp32_snaps.stl`: recommended controller fit sample.
- `fit_esp32.stl`: controller sample without snap tabs.
- `base.stl`, `lid.stl`: full enclosure. Base bounds are 78 × 40 × 15 mm;
  lid bounds in print orientation are 78 × 40 × 10.1 mm, including internal
  retention features. Assembled external height is 17 mm.
- `fit_sensor_snaps.stl`, `fit_sensor.stl`: unchanged sensor samples.
- `screw_test_base.stl`: 14 × 14 × 12 mm test block.
- `screw_test_cap.stl`: 14 × 14 × 2 mm countersunk test cap.
- `enclosure.scad`, sample SCAD files, `screw_test.scad`: geometry sources.
- `preview_controller.png`: empty sample and simplified controller model.
  `preview.png`: enclosure from STL. `preview_samples.png`: both fit samples.
- `build_enclosure.py`, `build_samples.py`, `build_fastener_test.py`: Python
  generators using numpy, manifold3d, trimesh, matplotlib and Pillow. STL was
  generated directly by the geometry kernel; SCAD was not independently
  compiled in OpenSCAD.
- `validation*.json`: digital check reports. `check_mount.py` and
  `check_usb_profile.py`: additional mount and USB checks. Saved sensor fixture
  hashes remove the dependency on a neighboring v0.7 directory.

## Validation and limits

All eight exported STLs were reopened: closed surfaces, consistent winding,
one connected body each. Digital checks found no intersections between the
base/lid and assumed PCB/component envelopes; idealized vertical PCB insertion
and lid removal were checked.

Total controller bearing area is 6.4 mm². It is unchanged with modeled corner
chamfers of 1, 1.5 and 2 mm and with true R2 rounded corners. This shows that
supports do not depend on corners within that range. Exact solder and component
placement was not modeled.

The USB end is nominally on the outside wall in both sample and enclosure;
the opening profile was checked directly in the STL. Physical fit confirmation
applies to the user's sample. It does not validate every cable, print shrinkage,
snap lifetime or screw/thread combination. Sensor, OLED, USB, flash history and
Wi-Fi were later tested separately; accuracy inside the fully assembled
printed enclosure remains unverified.

## Reproduce the geometry

Use Python 3.12+ and install the pinned `requirements-cad.txt` dependencies.
Run these commands from the repository root:

```bash
.tooling/venv/bin/python enclosure/v0.8/build_enclosure.py
.tooling/venv/bin/python enclosure/v0.8/build_samples.py
.tooling/venv/bin/python enclosure/v0.8/build_fastener_test.py
.tooling/venv/bin/python enclosure/v0.8/check_mount.py
.tooling/venv/bin/python enclosure/v0.8/check_usb_profile.py
```

Generators overwrite the delivered STL, SCAD, previews and reports. Review the
resulting diff, slicer geometry and previews before accepting regenerated files.
