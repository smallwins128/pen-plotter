; T13 - speed and acceleration ramp test. NO pen commands, NO homing needed.
; 5 laps of a 60 mm square plus both diagonals. Every lap sums to zero,
; so it must finish exactly where it started.
;
; Tape the pen down first: the drawing IS the measurement. On each lap the
; line should retrace the previous one. Lines fanning out = lost steps.
;
;   Place the pen with 70 mm of clear room LEFT and BEHIND it.
G21
G90
G94
G91
G1 F3000 X-60 Y0
G1 X0 Y60
G1 X60 Y0
G1 X0 Y-60
G1 X-60 Y60
G1 X60 Y-60
G1 X-60 Y0
G1 X0 Y60
G1 X60 Y0
G1 X0 Y-60
G1 X-60 Y60
G1 X60 Y-60
G1 X-60 Y0
G1 X0 Y60
G1 X60 Y0
G1 X0 Y-60
G1 X-60 Y60
G1 X60 Y-60
G1 X-60 Y0
G1 X0 Y60
G1 X60 Y0
G1 X0 Y-60
G1 X-60 Y60
G1 X60 Y-60
G1 X-60 Y0
G1 X0 Y60
G1 X60 Y0
G1 X0 Y-60
G1 X-60 Y60
G1 X60 Y-60
G90
