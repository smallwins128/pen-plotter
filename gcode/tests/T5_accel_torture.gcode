; T5 - acceleration tuning. Fast zigzag at full feed, PEN UP, returns to origin.
; Run, then check the pen is back exactly on the start mark.
; Raise $120 and $121 together (200 -> 300 -> 400), re-running this each time.
; The first value that loses position is the ceiling - back off 30 %.
G21
G90
G94
M3 S140
G4 P0.30
G0 X0 Y0
G1 F2000 X40 Y40
G1 X0 Y0
G1 X40 Y0
G1 X0 Y40
G1 X40 Y40
G1 X0 Y40
G1 X40 Y0
G1 X0 Y0
G1 X40 Y40
G1 X0 Y0
G1 X40 Y0
G1 X0 Y40
G1 X40 Y40
G1 X0 Y40
G1 X40 Y0
G1 X0 Y0
