# CLAUDE.md: pen-plotter (shared by four rooms)

This repo holds the code and CAD for four of Allwin's rooms. Room state lives in each room's Drive Handoff,
not here: open the room first (room-open), then work. This file only maps the repo to the rooms.

| Room | What it is | Handoff (Drive ID) | Paths |
|---|---|---|---|
| R04 Etch | The pen plotter: frame, gantry, pen lift, electronics, firmware, art | `[R04 Etch] Handoff` `1yfa4qkQ8ijbC7aNmVGBLoFzkRc013_VTP9oSZZtAV_Y` | `docs/` (start: `docs/GANTRY_STATE.md`, `docs/ENCLOSURE_STATE.md`), `hardware/gantry/`, `hardware/parts/` (except the room folders below), `hardware/sheet/`, `firmware/`, `settings/`, `gcode/`, `tools/` |
| R05 Harbor | The workshop room: bench wall, storage, printer tower | `[R05 Harbor] Handoff` `18dXq108vnKKHk6p__GAn0ptqfe2LGe-6ejdjxAlNe7o` | `hardware/parts/harbor/`, `hardware/labels/`, `hardware/web/build_harbor.py`, `hardware/web/lofi/` (Harbor pages), `hardware/web/reel/` |
| R06 Beacon | The bench light arm (WiZ batten) | `[R06 Beacon] Handoff` `1Axq1d-6nGde2UpiD90hrValqUOIzOL3ZuoGo07It9Mo` | `hardware/parts/beacon/` |
| R09 Cedar | The bench power supply (ATX PSU on DIN rails) | `[R09 Cedar] Handoff` `1wCbPwAk5kZXNV6Ek9YYDzminYv0DLPmG4SsWq8wWZvk` | `hardware/parts/cedar/`, `hardware/web/cedar_inspector.html` |

## Rules
- Ask Allwin before merging anything into `main`. Work on a `claude/<room>-<topic>` branch. After a merge, tell the
  other rooms that share this repo to pull.
- Keep `hardware/parts/washers.py` (on branch `claude/etch-pen-lifter-7woi1t`, not yet merged) when that branch
  is merged or cleaned up.
- Screws follow Allwin's standards: one core screw type per size (build-fasteners skill). CSK for 3D prints.
- Before deleting a claude.ai artifact, archive it in `docs/archive/artifacts/`, along with any data files it
  loads (see the README there).
- Run each part's check script before pushing (for example `python3 hardware/gantry/frame.py`). The CAD needs
  build123d (`hardware/requirements.txt`), which needs Python 3.10 or newer.
- Harbor Now and Plans are built from `hardware/web/lofi/` by `hardware/web/build_harbor.py`. Edit the source,
  never just the live page (room-now skill).
