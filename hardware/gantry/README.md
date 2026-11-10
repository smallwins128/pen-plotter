# Gantry

Parts and the inspector for the plotter's frame, gantry, carriage and pen lift. State and decisions:
`docs/GANTRY_STATE.md`.

- `acro_plates.py`: reads the OpenBuilds ACRO plate STL, splits it into its 11 parts, traces outlines and holes.
- `gantry_lofi.py`: writes `hardware/web/lofi/gantry_lofi.html` (parts, rail section, bay top view) from that
  STL plus `params.py`.
- `acrylic/`: put `Openbuilds_ACRO_Plates.stl` here (Drive: R04 Etch, file id `1GCvAh8MUwtIzEuWDRKBjuIZjAEE99_Pn`;
  originally Printables model 260803). It is git-ignored until its licence is checked, because this repo is public.
