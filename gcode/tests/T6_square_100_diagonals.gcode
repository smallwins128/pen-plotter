; T6 - squareness. 100 mm square plus both diagonals, pen down.
; Measure the two diagonals. Equal = gantry square (expect 141.4 mm).
; Unequal = the dual-X beam is racked; re-square it per SETUP.md phase 4.3.
G21
G90
G94
M3 S160
G4 P0.30
G0 X0 Y0
M3 S120
G4 P0.30
G1 F1200 X100 Y0
G1 X100 Y100
G1 X0 Y100
G1 X0 Y0
M3 S160
G4 P0.30
G0 X0 Y0
M3 S120
G4 P0.30
G1 X100 Y100
M3 S160
G4 P0.30
G0 X100 Y0
M3 S120
G4 P0.30
G1 X0 Y100
M3 S160
G4 P0.30
G0 X0 Y0
