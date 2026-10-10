# Enclosure handoff — from plastic boxes to one stainless enclosure

Start a new chat with this file. It records where the electronics enclosure
work stands, what was decided and why, and what is next.

## Where it stands

The proof of concept was two plastic carry cases, hinge to hinge: a **PSU box**
(mains, both PSUs, buck, PSU panel) and a **control box** (drivers, board, GX16
panel, receiving jack panel). That route is being **abandoned** in favour of a
single 1 mm stainless enclosure. Everything below that is still useful carries
over.

## What exists in the repo

| File | What it is |
|---|---|
| `hardware/parts/wire_jig.py` | Stick-on wire guides: N x 4 mm channels, 1.5 mm walls, flanged base. Straight (10 mm long) and 90-degree bend. Printed and in use. |
| `hardware/parts/link_panel.py` | Flanged, 3D-printed panels: `psu` (3 rows jack / label / display / toggle + G1, G2), `ctrl` (5 receiving jacks), `gx` (6 x GX16). Also `draw_lids()`/`check_lids()` for the old box lids. |
| `hardware/print_sheets.py` | 1:1 A4 cutting templates per panel, and colour wire labels (one row per wire) plus panel pocket labels. |
| `hardware/sketches/psu_box_layout.py` | The PSU box as built (traced from a photo). |
| `hardware/sketches/psu_lid_wiring.py` | The PSU lid DC wiring plan, no crossings. |

`python3 hardware/parts/link_panel.py`, `python3 hardware/print_sheets.py` and
the two sketches regenerate everything into `hardware/out/` (git-ignored).

## Parts confirmed from datasheets

| Part | Key numbers |
|---|---|
| 4 mm banana binding post (Sharvi) | M12 x 0.75 body, panel hole 12 +/- 0.1 (model uses 12.2), cap 14.5 dia, 23.5 long, M4 x 0.5 rear stud + 2 nuts, 32 A |
| KN3(A)-101 toggle, SPST ON-OFF | M12 x 0.75 bushing, hole 12.2 with 1.9 x 0.9 key slot, body 28 x 16 x 17 (+7 terminals), 15 A **250 VAC** (no DC rating given) |
| 0.36" 2-wire voltmeter, 2.5-30 V | display block 22.70 x 10.42 x 7.5, PCB 30.40 across the ears. Ear hole pitch **26.6 is an estimate — measure** |
| GX16 aviation sockets | 16 mm hole; 3 x GX16-5 (X1, X2, Y steppers, 4 wires + shield), 2 x GX16-3 (X, Y endstops), 1 x GX16-4 (pen servo) |
| M3 countersunk (DIN 7991) | panel corner screws, 6.4 mm 90-degree countersink |

## Power, as built so far

- **Supplies:** LRS-350-24 (24 V), a second PSU at **12 V**, and a buck converter **12 V -> 6 V** for the servo.
- **Grounds:** G1 = 24 V return. G2 = 12 V and 6 V return, because the buck is not isolated and is fed from the 12 V supply. Never join G1 and G2 anywhere except the one star point.
- **Mains:** IEC (switched, fused) -> lever splitter -> L / N / PE to both PSUs. Both PSU FG terminals to PE.
- **DC distribution:** a PCT 2x6 (two separate 1-in / 3-out splitters) splits 12 V (12 V switch, buck +, fan +) and G2 (buck -, fan -). Pass-through connectors make each panel unpluggable.
- **Panel wiring:** PSU -> switch -> jack. The display red goes after the switch (so it doubles as the "rail on" light), and the display black goes to that rail's own ground.
- **Jack lugs:** insulated M4 ring terminals. Blue (1.5-2.5 mm²) for 24 V and G1, red (0.5-1.5 mm²) for 12 V, 6 V and G2.
- **No fuses.** The PSUs current-limit, so 24 V and G1 wire must be 1.5 mm² or heavier.
  **16 AWG is 1.31 mm² and does not meet that** — buy metric 1.5 mm² or 14 AWG. The 12 V,
  G2 and 6 V wire is sized to the 12 V supply's and the buck's own current limits (read
  the 12 V supply's label). Why the mains inlet fuse cannot stand in for a DC fuse, and the
  rest of the wire-size arithmetic: [FINDINGS.md §11](FINDINGS.md). POWER.md's F1 / F2 are
  superseded by this decision.

## Flags still open

1. **Buck rating vs servo.** If the buck is an LM2596 board (~2 A real), a 2.5 A servo stall can brown it out. POWER.md already names this failure. A 5 A buck (XL4015) is the fix.
2. **Toggle DC rating.** KN3(A)-101 lists only 15 A at 250 VAC. Fine for a few amps at 24 V DC; do not switch near 10 A DC with it.
3. **Mains wire colours** in the PSU box were red / yellow / green. Use brown / blue / green-yellow, or label them.

## Next: one 1 mm stainless enclosure (user to share a wireframe)

The intent, as stated:

- **Shell:** 1 mm stainless sheet, with panel holes cut in.
- **Lid:** top + back as one removable piece. Sides, base and front form the fixed working space.
- **Mains entry:** from either side.
- **GX16 plate:** on the front, toward the top. That face may be angled.
- **The banana jack link panels may now be redundant:** with mains and control in one box there is no box-to-box link. The display + toggle idea could survive as a front "rails" panel.

Things that change with a metal box:

- **The enclosure must be bonded to mains PE** (IEC earth pin -> a stud on the shell, ring terminal, star washer).
- **DC 0 V stays floating from PE** (POWER.md's argument still stands). GX16 shells will touch the stainless, so carry the motor cable shields to the 0 V star through **pin 5**, not through the connector shell.
- **Panel step depth:** `link_panel.py` panels have a 2 mm locating step (`BOSS_H`). Set it to the sheet thickness (1 mm) when panels are reused.
- **Removable top + back:** keep everything that needs servicing reachable from the top. Run only flexible, strain-relieved leads to anything mounted on the removable piece (fans, if they go there), ideally through a pass-through connector so it lifts off cleanly.
- **Mounting plate:** mount the PSUs, drivers and board on an internal plate that lifts out, rather than drilling the shell for every part.

## Observations from the decision to switch

- **1 mm stainless is very doable.** Have the panel holes laser-cut by the fabricator from a DXF (the GX16, jack, toggle and display cutouts are already defined in `link_panel.py`), instead of cutting by hand.
- **One box removes the hinge problem entirely.** No wires cross a moving joint, so the two-bundle hinge crossing, the lid pass-throughs and the "keep clear" corner from the box layout all go away.
- **The box-to-box link goes away too:** the five banana jacks, the jumper cable and the receiving panel. 24 V, 12 V and 6 V now go straight from the PSUs and buck to the distribution inside the one box.
- **The toggle + display rows are still worth keeping** as a front "rails" panel: per-rail switch, live voltage readout, and a binding post per rail for bench use. Its jacks become test points rather than the link.
- **Earthing:** earth stud on the shell from the IEC earth pin. DC 0 V stays off earth; stepper shields go to the 0 V star via GX16 pin 5, not the shell.
