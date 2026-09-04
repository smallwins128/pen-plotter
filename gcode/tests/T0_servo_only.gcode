; T0 - servo only, no motor motion.
; Five clean up/down cycles. Nothing should move except the pen carriage lever.
; PEN UP = S160, PEN DOWN = S120  <-- measured 2026-09-04 with tools/servo_sweep.py
; S155 is where the pen first lifts; S160 gives a little margin. Do NOT go near
; S180 - that is the end of the horn's travel and holding there resets the board.
G21
G90
G94
M3 S120
G4 P0.50
M3 S160
G4 P0.50
M3 S120
G4 P0.50
M3 S160
G4 P0.50
M3 S120
G4 P0.50
M3 S160
G4 P0.50
M3 S120
G4 P0.50
M3 S160
G4 P0.50
M3 S120
G4 P0.50
M3 S160
G4 P0.50
