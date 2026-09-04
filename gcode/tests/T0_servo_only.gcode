; T0 - servo only, no motor motion.
; Five clean up/down cycles. Nothing should move except the pen carriage lever.
; PEN UP = S140, PEN DOWN = S90  <-- set 2026-09-04 after the arm was re-aligned.
; Do NOT push pen-up towards S180: on the previous alignment that was the end of
; the horn's travel, and simply holding it there reset the board.
G21
G90
G94
M3 S90
G4 P0.50
M3 S140
G4 P0.50
M3 S90
G4 P0.50
M3 S140
G4 P0.50
M3 S90
G4 P0.50
M3 S140
G4 P0.50
M3 S90
G4 P0.50
M3 S140
G4 P0.50
M3 S90
G4 P0.50
M3 S140
G4 P0.50
