; T14 - reversal torture. 20 sharp serpentine turns, PEN OUT, no servo.
; Does the board survive repeated 180 degree direction reversals at F500?
; Both field-art resets happened inside a turnaround; this isolates that.
;
; 40 mm rows, 2 mm apart. About 2 minutes. Returns to the start point.
; Needs 40 mm clear to the RIGHT and 40 mm BEHIND the start point.
;
; Run:  python3 plot2.py --no-home --unlock T14_reversal_sharp.gcode
G21
G90
G94
G91
G1 F500 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y2.000
G1 X40.000 Y0.000
G1 X0.000 Y2.000
G1 X-40.000 Y0.000
G1 X0.000 Y-38.000
