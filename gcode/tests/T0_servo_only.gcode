; T0 - servo only, no motor motion.
; Five clean up/down cycles. Nothing should move except the pen carriage lever.
; PEN UP = S120, PEN DOWN = S60  <-- edit both to your values from tools/servo_sweep.py
G21
G90
G94
M3 S90
G4 P0.50
M3 S120
G4 P0.50
M3 S60
G4 P0.50
M3 S120
G4 P0.50
M3 S60
G4 P0.50
M3 S120
G4 P0.50
M3 S60
G4 P0.50
M3 S120
G4 P0.50
M3 S60
G4 P0.50
M3 S120
G4 P0.50
