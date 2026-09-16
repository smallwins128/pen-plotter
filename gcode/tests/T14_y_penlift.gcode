; T14 - Y travel + pen lift, ten cycles.
;
; The pattern a real plot actually makes: travel with the pen UP, stop, then
; actuate the servo. That is the combination FINDINGS.md section 7 records as the
; open failure - motion alone passes, servo alone passes, together they reset.
;
; The pen is never down while an axis is moving, so nothing is dragged across
; the paper and the only thing under test is servo-actuation-after-a-move.
;
; G91 RELATIVE - needs no work zero and no homing. Every cycle returns to where
; it started, so the machine ends where it began.
;
; PEN UP = S120, PEN DOWN = S60   <-- edit both if your values differ
; Y travel = 20 mm each way       <-- needs 20 mm of clearance in -Y
;
; Run it:  python3 plot2.py --no-home --unlock --force T14_y_penlift.gcode
;   --force because this file is relative and does not need the G54 offset that
;   plot2.py normally insists on.
;
; Ends PEN UP.

G21                     ; mm
G90                     ; absolute (modal default; G91 set below)
G94                     ; units per minute

; --- soft-start the servo (FINDINGS.md section 6) ------------------------
; It is limp until the first M3, and jumping straight to an extreme from limp
; is the largest current step it ever makes. Wake at centre and walk it out.
M3 S90
G4 P0.50
M3 S100
G4 P0.30
M3 S110
G4 P0.30
M3 S120
G4 P0.30

G91                     ; relative from here on

; --- cycle 1 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 2 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 3 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 4 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 5 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 6 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 7 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 8 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 9 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- cycle 10 ---
G0 Y-20
M3 S60
G4 P0.30
M3 S120
G4 P0.30
G0 Y20
M3 S60
G4 P0.30
M3 S120
G4 P0.30

; --- park: pen UP. No M2, no M30, no M5. ---------------------------------
M3 S120
G4 P0.30
