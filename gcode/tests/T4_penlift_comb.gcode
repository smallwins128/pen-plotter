; T4 - pen lift reliability. Eight 10 mm dashes, 5 mm gaps, one lift per gap.
; Every dash the same length and weight; gaps genuinely blank.
; Tails or dots in the gaps = increase the G4 P dwell after each pen change.
; PEN UP = S120, PEN DOWN = S60  <-- edit to your values
G21
G90
G94
M3 S120
G4 P0.30
G0 X0 Y0
M3 S60
G4 P0.20
G1 F1200 X10 Y0
M3 S120
G4 P0.20
G0 X15 Y0
M3 S60
G4 P0.20
G1 X25 Y0
M3 S120
G4 P0.20
G0 X30 Y0
M3 S60
G4 P0.20
G1 X40 Y0
M3 S120
G4 P0.20
G0 X45 Y0
M3 S60
G4 P0.20
G1 X55 Y0
M3 S120
G4 P0.20
G0 X60 Y0
M3 S60
G4 P0.20
G1 X70 Y0
M3 S120
G4 P0.20
G0 X75 Y0
M3 S60
G4 P0.20
G1 X85 Y0
M3 S120
G4 P0.20
G0 X90 Y0
M3 S60
G4 P0.20
G1 X100 Y0
M3 S120
G4 P0.20
G0 X105 Y0
M3 S60
G4 P0.20
G1 X115 Y0
M3 S120
G4 P0.20
G0 X0 Y0
