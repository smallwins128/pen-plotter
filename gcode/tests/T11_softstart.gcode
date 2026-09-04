; T11 - soft-start the servo, then the same 20 mm square as T9.
; The servo is limp until the first M3. Jumping straight to an extreme is the
; largest current draw it ever makes. This walks it up in stages instead.
G21
G90
G94
M3 S120
G4 P0.50
M3 S133
G4 P0.30
M3 S146
G4 P0.30
M3 S160
G4 P0.30
G91
G1 F500 X-20 Y0
M3 S120
G4 P0.30
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
M3 S160
G4 P0.30
G90
