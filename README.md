# pen-plotter

DIY pen plotter: IKEA LINNMON frame, aluminium extrusion gantry, GT2 belts, dual-X /
single-Y, NEMA 17s on A4988s, Arduino Uno + CNC Shield V3 running GRBL 1.1, and a
positional servo pen lift on D11.

## Start here

| | |
|---|---|
| **[docs/SETUP.md](docs/SETUP.md)** | The whole build, phase by phase: pin map, wiring, driver current, settings, bring-up ladder, daily run procedure, alarm/error reference. |
| **[docs/FIRMWARE_SERVO.md](docs/FIRMWARE_SERVO.md)** | Why stock GRBL cannot drive a hobby servo, and the four edits that fix it. Do this first — nothing in the pen-lift chain works until it is done. |
| **[docs/HANDOFF.md](docs/HANDOFF.md)** | **Start a new chat with this.** Current verified state of the machine: what works, what doesn't, the three workflow rules, and the open problem. |
| **[docs/FINDINGS.md](docs/FINDINGS.md)** | What commissioning actually taught us — the servo ground wire, the zero-work-offset crash, the EEPROM rule, servo soft-start, and what is still open. Read this before re-debugging anything. |
| **[docs/UGS.md](docs/UGS.md)** | Driving the machine by hand from Universal Gcode Sender: connect, unlock, work zero, macros for the pen, and the UGS buttons that do the wrong thing here. Manual work only — `plot2.py` still streams the plots. |
| **[settings/plotter.grbl.txt](settings/plotter.grbl.txt)** | Restore block for after a re-flash (which wipes EEPROM). |
| **[gcode/tests/](gcode/tests)** | T0–T6 bring-up tests, in the order you should run them. |
| **[tools/plot2.py](tools/plot2.py)** | The sender. Homes in the same connection it streams in, refuses to run without a work offset, `--lockstep` for one-line-at-a-time. |
| **[tools/servo_sweep.py](tools/servo_sweep.py)** | Interactive finder for the pen-up / pen-down S values. |

## The machine

| Part | Detail |
|---|---|
| Frame | IKEA LINNMON 100 × 60 cm, aluminium extrusion gantry |
| Motion | GT2 belt, 20-tooth pulleys; dual-X gantry (2 motors) + single Y |
| Motors | NEMA 17, harvested Ender-3 42-34, ~0.84 A/phase |
| Drivers | A4988 on CNC Shield V3, 1/16 microstepping |
| Controller | Arduino Uno + CNC Shield V3, GRBL 1.1h with servo timer patch |
| Pen lift | Positional servo on D11, driven by `M3 S<n>` |
| Usable area | ~150 × 150 mm comfortable |
| Limit switches | X and Y, both NC. No Z switch — D12 is jumpered to GND. |

**Orientation**, standing in front of the table: +X right, +Y away from you, home corner
front-right (`$H` drives +X and −Y). Drawings are authored in Quadrant I from a work zero
at the paper's bottom-left. Mirroring is fixed with `$3`, never by flipping G-code.

## G-code conventions

mm (`G21`), absolute (`G90`) for anything long enough to want to resume, feeds ≤ F2000,
`M3 S<up>` / `M3 S<down>` for the pen, **no Z words**, **no `M2`**, **no mid-file `M5`**.
Reasons for each in [docs/SETUP.md](docs/SETUP.md) phase 7.2.
