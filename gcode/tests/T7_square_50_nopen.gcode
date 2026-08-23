; T7 - 50 mm square, NO pen commands at all.
; No M3, no G4, no spindle. Pure X/Y motion.
; Isolates whether the pen/spindle command path is what stalls GRBL.
G21
G90
G94
G0 X0 Y0
G1 F500 X50 Y0
G1 X50 Y50
G1 X0 Y50
G1 X0 Y0
