; T8 - same square, but a tiny servo swing (S105 up / S90 down, ~15 units).
; Diagnostic: a smaller pen movement draws a smaller current pulse.
G21
G90
G94
M3 S105
G4 P0.30
G0 X0 Y0
M3 S90
G4 P0.30
G1 F1200 X50 Y0
G1 X50 Y50
G1 X0 Y50
G1 X0 Y0
M3 S105
G4 P0.30
G0 X0 Y0
