# Control box — one inlet, one rail, nineteen wires

An enclosure holding the PSU, the Uno and the shield, presenting every machine wire on a
keyed panel connector. Written to be built in the order given; each phase ends in a check.

**Status: design only. Nothing here has been built or measured.** Every number is either
from a datasheet (marked) or arithmetic from the loads in [SETUP.md](SETUP.md). Treat the
mechanical dimensions as a starting point, not as measured fact.

> **Do this after the servo reset is fixed, not before.** The open fault in
> [HANDOFF.md §7](HANDOFF.md) is unresolved. Build an enclosure around it and you will be
> debugging it through a lid. Cap at the servo, twist the pairs, shorten the arm, confirm
> clean — then build the box.

---

## 1. Why three supplies collapse into one

The sketch was one mains inlet feeding three PSUs: shield, Arduino, servo. It needs one.

| Load | Thought it needed | Actually needs |
|---|---|---|
| CNC shield / steppers | 24 V | 24 V |
| Arduino | its own 5 V | nothing — it runs on USB, and the USB **data** link to the Mac has to be there regardless. A second 5 V source only fights the on-board regulator. |
| Endstops | a supply | nothing — they are bare switches to GND. GRBL's internal pull-ups drive them (`limits.c`). |
| Servo | its own 6 V | a DC-DC from the 24 V. No one makes a 6 V mains PSU, so this was always going to be a converter. |

So: **one 24 V brick, one fused distribution block, one 0 V star point.** Common grounds
stop being something you wire correctly and become something the topology guarantees.

### Load budget

```
3 × NEMA 17 @ 0.84 A/phase, 24 V chopper      ~1.2 A worst case
pen branch (UBEC 6 V × 2.5 A stall ÷ 24 V ÷ η) ~0.7 A
60 mm fan                                      ~0.1 A
                                              --------
                                              ~2.0 A
```

**Mean Well LRS-100-24** — 24 V, 4.5 A, flat enclosed brick, ~130 × 100 × 30 mm. Roughly
2× headroom. The LRS-350-24 you already own works identically at 6 % load; it is 215 mm
long, so the box grows to about 400 mm. Free, but bigger.

---

## 2. Power topology

```
  230 V ─► IEC C14 inlet ─► LRS-100-24 ─► +24 V BLOCK ─┬─ F1 3 A ──► shield V+
           fused T2 A                                  ├─ F2 1.5 A ► PEN pin 1
           switched                                    └─ F3 0.5 A ► fan
              │                                             (returns)
              │ PE                                              │
              ▼                                                 ▼
        ┌───────────┐        ✗ no bond         ╔═══════════════════════════╗
        │ PE block  │· · · · · · · · · · · · · ║  0 V — STAR POINT (block) ║
        │ + chassis │                          ╚═══════════════════════════╝
        └───────────┘                             ▲      ▲       ▲      ▲
                                             PSU −V  shield  PEN pin 2  fan −
                                                     GND
```

**The dashed link is the one you must not make.** The Mac's USB cable already ties 0 V to
the building earth through the laptop. Bonding 0 V to PE inside the box adds a second path
and puts a ground loop around the serial line — on a machine whose entire failure history
is grounding, that is not a risk worth taking. The PSUs are isolated; leave DC floating.

### Fusing

| | Rating | Protects |
|---|---|---|
| Inlet | T2 A slow-blow | ~0.5 A at 230 V for a 100 W supply; slow-blow rides the inrush |
| F1 | 3 A | stepper branch (~1.2 A) |
| F2 | 1.5 A | pen branch (~0.7 A), sized above UBEC inrush |
| F3 | 0.5 A | fan |

---

## 3. Panel — where the 19 wires land

12 stepper + 4 endstop + 3 pen = 19 conductors, on six ports.

```
   left end          ┌─────────────── 300 mm front face ───────────────┐
   ┌──────┐          │                                                 │
   │ IEC  │  keep    │   (X)      (A)      (Y)     (LIM)  (PEN)  [USB] │   right end
   │ C14  │  clear   │  GX16-4   GX16-4   GX16-4   GX12-4 GX12-3   B   │   ┌──────┐
   └──────┘  PSU     │   16mm     16mm     16mm     12mm   12mm        │   │ fan  │
             behind  └─────────────────────────────────────────────────┘   └──────┘
```

**Steppers get GX16 (16 mm hole), endstops and pen get GX12 (12 mm).** Different shell
diameters, so a stepper lead physically cannot be pushed into the pen port. That matters
more than a label, because **PEN pin 1 is 24 V** and a servo plugged into it dies instantly.

Mains enters the **left end panel** and never crosses the front face. Fan on the opposite
end. The left quarter of the front face stays clear because the PSU sits behind it.

### Pin schedule

**X / A / Y — GX16-4, three off**

| Pin | Signal |
|---|---|
| 1 | A+ |
| 2 | A− |
| 3 | B+ |
| 4 | B− |

Wire to the driver's motor header in the socket's own order. **Identify coil pairs with a
meter** — continuity means same coil. Ender colour codes vary between batches; do not
trust them.

**LIM — GX12-4**

| Pin | Signal | To |
|---|---|---|
| 1 | X SIG | X endstop header signal (D9) |
| 2 | X RTN | a shield GND **pin** |
| 3 | Y SIG | Y endstop header signal (D10) |
| 4 | Y RTN | a shield GND **pin** |

NC switches, polarity irrelevant (SETUP §3.1). Two-pair screened cable; drain to shield
GND at the **box end only** — grounded at both ends it is a loop antenna.

**PEN — GX12-3**

| Pin | Signal | To |
|---|---|---|
| 1 | +24 V | F2 |
| 2 | 0 V | star block |
| 3 | SIG | D11 — the header silkscreened `Z+/Z−` (SETUP §2) |

---

## 4. Interior arrangement

Plan view, lid off, front face at the bottom:

```
 ┌──────┬───────────────────────────┬──────────────────────────────┐
 │VENTS │                           │   DIN mini-rail (~90 mm)     │
 │      │                           │  ┌──┬──┬──┬───┬────┐         │
 │ IEC  │      LRS-100-24           │  │PE│F1│F2│+24│0V ★│         │
 │ C14  │   (base-mounted brick)    │  └──┴──┴──┴───┴────┘         │
 │      │                           │                              │
 ├──────┴─ mains barrier ───────────┤                              │
 │                                  │                         ┌────┤
 │              ┌──────────────────┐│      ◄── airflow ───────│FAN │
 │              │  UNO + SHIELD    ││                         └────┤
 │              │  drivers up,     ││                              │
 │              │  heatsinks on    ││                              │
 │              └──────────────────┘│                              │
 └───(X)───(A)───(Y)────(LIM)─(PEN)─[USB]───────────────────────────┘
```

**Why the PSU sits along the back:** it frees the whole 300 mm front face. Put the supply
along the left end instead and six ports have to crowd into 170 mm — under 30 mm centres,
closer than a GX16 backshell lets you tighten.

Enclosure: **≥ 300 × 200 × 80 mm internal.** ABS, or diecast aluminium bonded to PE.

---

## 5. Grounding — what lands where

| Node | Lands on | Why |
|---|---|---|
| PSU −V | 0 V star block | source of the node |
| Shield GND | 0 V star block | one 0.75 mm² wire; stepper return flows here |
| PEN pin 2 | 0 V star block | servo supply return **and** signal reference |
| Fan − | 0 V star block | — |
| LIM pins 2, 4 | shield GND **pins** | *not* the star block — keeps the switch reference off the stepper return path |
| Cable screen | shield GND, box end only | both ends = loop antenna |
| D12 | any shield GND pin | the mandatory jumper (SETUP §3.2) |
| PE / chassis | earth block only | never bonded to 0 V |

Land every return **on the block**. No daisy chains between loads.

---

## 6. The one non-obvious move: regulate at the servo

HANDOFF §7's prime suspect is 1.5 m of thin wire between the buck and an MG996R.
Centralising power in a box makes that run *longer*. So don't send 6 V up the umbilical —
send 24 V, and put the step-down on the carriage.

```
NOW:   [LM2596 in box, 6 V] ══ 1.5 m thin pair, 2.5 A step ══► [MG996R]   resets the Uno

NEW:   [PEN port, 24 V]  ── 1.5 m, ~0.7 A steady ──► [UBEC 6.0 V] ─80 mm─► [MG996R]
                                                     + 2200 µF        on the carriage
```

The 2.5 A transient shrinks from a 1.5 m loop to an 80 mm one, and the umbilical carries a
smooth ~0.7 A that the UBEC's input capacitance has already softened. Voltage at the
regulator is now voltage at the servo, which is the thing that was not true before.

Two more things this buys:

- **Pin 2 doubles as the servo's signal return**, so the `VOUT−` → shield GND wire that
  [FINDINGS §2](FINDINGS.md) says must never be removed becomes structurally impossible to
  omit — it is a conductor in the umbilical, not an extra wire someone can tidy away.
- The LM2596 goes. It is a ~2 A part being asked for 2.5 A. A 6 V-selectable UBEC rated
  ≥ 5 A is built for exactly this current profile.

Still three wires. If you later want the last few dB, run a 4-core and give the PWM its own
return to a shield GND pin. At 0.7 A the shared-return offset is tens of millivolts against
a 5 V logic threshold — it was the 2.5 A version of that same wire that was killing you.

---

## 7. Build order

Each step ends in a check. Do not start the next until it passes.

**7.1 — Drill and dry-fit, no wire.** 16 mm × 3, 12 mm × 2, USB cutout, IEC rectangle,
60 mm fan + four M4 on 50 mm centres. Drop all six connectors in loose.
→ *Check:* every backshell tightens without fouling its neighbour, and the lid closes over
the driver heatsinks.

**7.2 — Mains, complete and covered, before any DC.** 0.75 mm², ferrules on every
conductor. Inlet L/N to the PSU input; inlet earth to the PE block; PE block to the PSU
earth terminal and to the box metalwork. Shroud the inlet and PSU input terminals
(SETUP §0).
→ *Check:* plug in, switch on, meter 24 V at the PSU output, switch off. Nothing else
connected.

**7.3 — DC distribution and the star point.** +V to the +24 block, −V to the 0 V block,
F1/F2 in their branches.
→ *Check:* continuity from each 0 V landing to the block. **No** continuity from 0 V to PE.

**7.4 — Board in, bulk cap at its terminals.** Shield V+ and GND on 0.75 mm², with the
220–470 µF 50 V electrolytic right at the screw terminals (HANDOFF §7 fix 2). Short
USB-B lead to the panel socket. Re-fit the D12 jumper.
→ *Check:* USB only, 24 V off — `$I` returns `[VER:1.1h.plotter-servo-1:]`.

**7.5 — Endstops.**
→ *Check:* `?` with nothing pressed shows no `Pn:` field at all. Press each switch by hand:
`Pn:X`, then `Pn:Y`, each clearing on release. **Before homing** (SETUP §6.0).

**7.6 — Pen port and the carriage pod.** Build the pod first: UBEC, 2200 µF 16 V with its
striped leg to 0 V, legs trimmed short, anchored so it cannot flap. Set the UBEC to 6.0 V
**with the servo disconnected**, meter on the output (SETUP §3.3).
→ *Check:* T0 — five clean up/down cycles, no buzzing at either end, no reset.

**7.7 — Motors last.** Switch off at the panel for every plug and unplug. A panel connector
makes hot-plugging easy; hot-plugging a stepper is still the fastest way to kill an A4988
(SETUP §0).
→ *Check:* both X motors turn together on T1. If they fight, swap one coil pair on **one**
motor — not `$3`, which flips the whole axis.

**7.8 — Fan, lid, back to the ladder.**
→ *Check:* T1–T6 pass as before, drivers warm rather than hot after a long plot.

---

## 8. Power sequencing is preserved for free

The panel switch cuts **24 V only**; USB arrives separately from the Mac. So the documented
order survives without a second switch:

- **Up:** plug USB (GRBL boots, drives the enable line and D11 to a known state), then flip
  the panel switch.
- **Down:** panel switch off, then unplug USB.

That rocker is also the emergency stop — the one that still works when the terminal has
stopped listening (HANDOFF, Safety).

---

## 9. Parts

| Qty | Part | Note |
|---|---|---|
| 1 | Enclosure ≥ 300 × 200 × 80 mm internal | ABS or diecast ally; if metal, bond to PE |
| 1 | IEC C14 inlet, fused + switched | T2 A slow-blow; UK lead plugs straight in |
| 1 | Mean Well LRS-100-24 | 24 V 4.5 A. Or reuse the LRS-350-24 in a longer box |
| 3 | GX16-4 panel socket + plug | ~5 A/pin, far above the 0.84 A the motors draw |
| 1 | GX12-4 panel socket + plug | endstops |
| 1 | GX12-3 panel socket + plug | pen — different shell size on purpose |
| 1 | Panel USB-B ↔ USB-B pass-through | so the lid never comes off to re-flash |
| 1 | UBEC, 6 V selectable, ≥ 5 A | lives on the carriage, replaces the LM2596 |
| 1 | 2200 µF 16 V electrolytic | at the servo |
| 1 | 220–470 µF 50 V electrolytic | at the shield's 24 V terminals |
| 1 | 60 mm 24 V fan + finger guard | blowing in over the drivers |
| ~200 mm | DIN rail, PE block, 2 × 5×20 fuse carrier, 2 × distribution block | F1 3 A, F2 1.5 A |
| — | 0.75 mm² wire + ferrules, 3-core 0.5 mm² umbilical, 2-pair screened | the 0.5 mm² umbilical is what replaces the thin servo wire |

---

## 10. What this box does not do

**It does not fix the servo reset.** See the note at the top. The fixes queued in
HANDOFF §7 are mechanical and electrical at the servo end; none of them is an enclosure.

**It does not square the gantry, add a second X switch, or remove the Uno's ceiling.** If
you end up going ESP32/FluidNC (FINDINGS §7), the box, the panel connectors and the
umbilical all carry over unchanged — only the board on the standoffs changes. Nothing here
is wasted by that move.
