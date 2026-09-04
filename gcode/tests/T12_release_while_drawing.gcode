; T12 - soft start, pen down, then M5 to RELEASE the servo while drawing.
; M5 disconnects the PWM pin, so the servo draws no holding current at all
; during the strokes. The pen stays down under its own weight.
; Failures now happen during moves while the servo holds - this removes that.
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
G4 P0.50
M5
G4 P0.30
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
M3 S120
G4 P0.30
M3 S160
G4 P0.30
G90
