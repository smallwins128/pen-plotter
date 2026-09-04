; T10 - same 20 mm relative square as T9, but with a 1 second dwell
; BEFORE every pen command as well as after.
; Tests whether the supply simply needs time to recover after a move
; before the servo actuates.
G21
G90
G94
G4 P1.00
M3 S160
G4 P1.00
G91
G1 F500 X-20 Y0
G4 P1.00
M3 S120
G4 P1.00
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G4 P1.00
M3 S160
G4 P1.00
G90
