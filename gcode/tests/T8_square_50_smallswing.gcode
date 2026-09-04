; T8 - same square, but a tiny servo swing (S135 / S120, ~15 units).
; The swing sits just above pen-down and does NOT lift the pen clear - that is
; deliberate. This measures current draw against swing size, not drawing.
; Diagnostic: a smaller pen movement draws a smaller current pulse.
G21
G90
G94
M3 S135
G4 P0.30
G0 X0 Y0
M3 S120
G4 P0.30
G1 F1200 X50 Y0
G1 X50 Y50
G1 X0 Y50
G1 X0 Y0
M3 S135
G4 P0.30
G0 X0 Y0
