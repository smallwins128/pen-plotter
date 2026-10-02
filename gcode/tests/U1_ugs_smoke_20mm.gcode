; U1 - UGS smoke test.  20 mm square, PEN FREE, drawn RELATIVE to wherever the
; pen already is.  No servo commands at all, so it cannot trip the pen-lift
; reset, and no work offset needed - it never goes near X0 Y0.
;
; Safe straight after homing: it goes left and back first, and returns to its
; own start point.  About twenty seconds.
;
; What to watch:  the gantry traces a square and lands back where it started,
; and the console reaches Idle with no ALARM and no error.  Watch the machine,
; not the progress bar - the console reports success while the gantry is jammed.
G21
G90
G94
G91
G1 F500 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G90
