; T9 - 20 mm square with pen, drawn RELATIVE to wherever the pen already is.
; No long traverse to work zero - isolates "servo + short moves" from
; "servo + sustained long move". Safe to run straight after homing:
; it goes left and back first, and returns to its start point.
G21
G90
G94
M3 S120
G4 P0.30
G91
G1 F500 X-20 Y0
M3 S60
G4 P0.30
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
M3 S120
G4 P0.30
G90
