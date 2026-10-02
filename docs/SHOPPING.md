# Purchase list

Everything here is tied to a failure this machine actually produced. Nothing is on the
list because it is generally good practice.

_Written 2026-08-26, after three unexplained mid-plot resets with the servo disconnected._

---

## Read this before spending anything

**Two free tests may delete half this list.** Neither needs a purchase:

1. **Stream a full art file with the 24 V PSU OFF** (FINDINGS §7a). Nothing moves; GRBL
   runs the whole motion profile in software. A reset there means the motors are not
   involved at all, and every capacitor below is irrelevant.
2. **Swap the USB cable for any other one you own**, straight into the Mac, no hub.

Do them first. The list is ordered so that the items which are useful *regardless* of how
those tests come out are at the top.

---

## Tier 1 — measurement. You are currently flying blind.

| | Item | Spec | Why |
|---|---|---|---|
| 1 | **Digital multimeter** | DC volts to 0.01 V, continuity beeper | **`Vref` has never been measured on any of the three drivers.** That is the single largest unknown on the machine — wrong Vref means overheating, missed steps, or both. Also needed for the buck output, the 24 V rail, and proving the servo ground wire is continuous. |
| 2 | **Inline USB power meter** | USB-A pass-through, reads V and A | Tests the live hypothesis directly: does the 5 V USB rail sag when the steppers run? The Arduino is USB-powered, so this is the rail that matters. |

**Set Vref first thing.** Ender 42-34 motors are ~0.84 A/phase. Read `R100` or `R050` off
each driver board, then `Vref = I × 8 × R_sense`: **0.67 V** for `R100`, **1.34 V** for
`R050`. Meter on the pot, PSU on, motors connected, USB out.

## Tier 2 — the untested suspect: the USB path

The Arduino runs on USB power and the shield never feeds `VIN`, so a sag on the 24 V motor
rail **cannot brown out the board directly**. Either noise is coupling in through ground,
or the USB connection itself is dropping and the Mac is re-enumerating — which resets the
board exactly as opening the serial port does. This path has never been tested.

| | Item | Spec | Why |
|---|---|---|---|
| 3 | **Shielded USB cable** | USB-A → **USB-B**, 1 m, moulded ferrites | The Uno takes USB-B. Short and shielded. Cheapest possible fix if the cable is marginal. |
| 4 | **USB isolator** | ADuM3160 or ADuM4160, **full-speed 12 Mbps** | Breaks the ground loop between Mac and machine outright. If noise is arriving via USB ground this is the cure. Must be full-speed — low-speed-only boards will not carry the serial adapter. |
| 5 | **Clamp-on ferrite cores** | Assorted 5/7/9 mm bore, 10-pack, mix 31 or 43 | One on the USB cable at each end, one on each motor lead. Free to try, no wiring. |

## Tier 3 — power integrity. The fixes FINDINGS already queued.

| | Item | Spec | Why |
|---|---|---|---|
| 6 | **Electrolytic, servo** | **2200 µF 16 V**, low-ESR, 105 °C, ×2 | FINDINGS §7 fix 1. Fitted **at the servo end**, striped leg to ground, legs trimmed short. The MG996R pulls ~2.5 A stall down 1.5 m of thin lead. |
| 7 | **Electrolytic, shield** | **470 µF 50 V**, low-ESR, 105 °C, ×2 | FINDINGS §7 fix 2, across the shield's 24 V input terminals. A4988s need local bulk capacitance and the clone shield ships with almost none. 50 V on a 24 V rail is the right margin. |
| 8 | **Ceramic capacitors** | 100 nF 50 V, ×20 | In parallel with each electrolytic. Electrolytics are slow; the ceramic catches what they miss. |
| 9 | **Separate servo supply** | 6 V 3 A regulated, or 5 V 3 A USB charger + breakout | FINDINGS §7 step 1 — the decisive test of whether the LM2596 buck is the weak link. **6.0 V, not 5.2 V**: the MG996R is rated 4.8–7.2 V and was being starved. Ground it to the shield. |

## Tier 4 — wiring. Attacks the noise at source.

| | Item | Spec | Why |
|---|---|---|---|
| 10 | **Shielded twisted stepper cable** | 4-core, 22 AWG, shielded, ~10 m | FINDINGS §7 fix 3. Twisting A+/A− and B+/B− cancels the field each pair radiates. 1.5 m of untwisted lead per motor is an antenna. Ground the shield **at the controller end only**. |
| 11 | **Silicone wire** | 20 AWG, red and black, 3 m each | FINDINGS §6a: the servo's power pair must be 20 AWG or thicker. Signal can stay thin. |
| 12 | **JST-XH kit + crimp tool** | 2.54 mm, 4-pin, SN-28B crimper | Skip if you buy ready-made shielded stepper extensions instead. |
| 13 | **Heat shrink + sleeving + ties** | Assorted, 6 mm braided sleeve | Keeps the twisted pairs twisted and the runs off the signal wires. |

## Tier 5 — thermal. SETUP asks for this and it is not confirmed fitted.

| | Item | Spec | Why |
|---|---|---|---|
| 14 | **Driver heatsinks** | 9 × 9 × 5 mm adhesive, ×10 | "A4988s at 24 V run hot" — SETUP phase 4. A driver in thermal shutdown drops steps silently. |
| 15 | **Fan** | 40 mm, 24 V, + mount | Blowing across the drivers. |

## Tier 6 — spares, so a fault can be isolated instead of theorised

| | Item | Spec | Why |
|---|---|---|---|
| 16 | **Spare Arduino Uno** | R3 clone | EEPROM has been corrupted twice and the board resets for reasons unknown. A second board turns "is it the board?" from an argument into a five-minute swap. Re-flash it with `firmware/grbl-servo-plotter.zip`. |
| 17 | **Spare A4988 drivers** | ×5 | Cheap, and one dying driver looks exactly like a motion fault. |

## Tier 7 — optional, and each is a project rather than a part

| | Item | Spec | Why, and the catch |
|---|---|---|---|
| 18 | **TMC2209 drivers** | ×4, standalone step/dir | Quieter, cooler, better current regulation, far less switching noise than A4988s. **Not a drop-in:** different Vref formula, different microstep jumper mapping, and on some boards the pinout is reversed — check orientation before power-up or you will destroy them. Re-tune from scratch. |
| 19 | **ESP32 FluidNC controller** | MKS DLC32, or a FluidNC 6-pack | FINDINGS §7 "under consideration". Native `rc_servo` motor type: the pen becomes an ordinary Z move, and the whole hand-patched GRBL timer hack goes away — along with the risk of losing it to a re-flash. |

## Tier 8 — actually making the art

| | Item | Spec | Why |
|---|---|---|---|
| 20 | **Gel or rollerball pens** | 0.5 mm, blue and red, **3+ of each** | Each layer of the field pieces is **~36 m of continuous line**. That will drain most fineliners well before the end, and there is no resuming a relative file. Choose pens with a visible ink reservoir so you can see it coming. |
| 21 | **Paper** | Smooth, 200–250 gsm, A4/A3 | Effective line pitch is 0.6 mm. Textured paper blurs that and chews nibs. Hot-pressed, bristol, or marker paper. |
| 22 | **Low-tack tape** | Washi or artist's masking | 70+ minutes of a pen dragging across the sheet. It **will** move if you skimp here. |

---

## Do not buy

- **A bigger 24 V PSU.** It is a Mean Well LRS-350-24 — 14.6 A against three motors drawing
  0.84 A/phase. It has an order of magnitude of headroom and is not the weak link.
- **A stronger servo.** The MG996R is already oversized for the job. The problem is getting
  current *to* it, and FINDINGS §7 fix 4 notes that a 2.5 mm eccentric cam would need
  **twelve times less torque** than the current 30 mm crank. Geometry beats amperes here.
- **Anything to make 180 mm work.** Size was never what failed — the reset at line 3014 was
  mid-row, well inside the drawn area.

## If you only buy three things

**The multimeter, the USB cable and isolator, and the capacitor set.** Roughly a third of
the total, and between them they cover measurement, the untested suspect, and both queued
electrical fixes.
