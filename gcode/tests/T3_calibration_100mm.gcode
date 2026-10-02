; T3 - steps/mm calibration. Draws a 100 mm line along X and a 100 mm line along Y.
; Measure both with calipers, then:
;   $100_new = $100_old * (100 / measured_X)
;   $101_new = $101_old * (100 / measured_Y)
G21
G90
G94
M3 S140
G4 P0.30
G0 X0 Y0
M3 S90
G4 P0.30
G1 F1000 X100 Y0
M3 S140
G4 P0.30
G0 X0 Y0
M3 S90
G4 P0.30
G1 F1000 X0 Y100
M3 S140
G4 P0.30
G0 X0 Y0
