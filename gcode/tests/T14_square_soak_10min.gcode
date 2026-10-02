; T14 - 20 mm square, repeated 58 times, PEN FREE.  A soak test: ~10 minutes
; of continuous motion to shake out lost steps, belt slip, driver overheating
; and the mid-run resets.  One short square proves the machine moves; this
; proves it keeps moving.
;
; Relative (G91), so it needs no work offset and never goes near X0 Y0.
; Every lap returns to its own start point, and the square sits left of and
; behind wherever the pen is when you press send - the same safe envelope as
; T9 and U1.  Safe to run straight after homing.
;
; NO SERVO COMMANDS AT ALL.  It cannot trip the pen-lift reset, so if the
; controller resets during this run the cause is motion or power, not the pen.
;
; TIMING IS CALCULATED, NOT MEASURED: 58 laps at F500 with $110=500 and
; $120=50 works out at 10.27 s/lap = 9 min 55 s.  It assumes a full stop at
; each corner ($11=0.020 makes junction speed negligible), so the real run
; may come in slightly under.  Time the first run and correct this comment.
;
; WHAT TO WATCH
;   Drift.  Mark the start point on the bed with a pencil or a bit of tape
;   before you send.  After 58 laps the pen should be back on that mark.  If
;   it has walked, the machine is losing steps - which is what this test is
;   for.  Halve $120/$121 or drop the feed and run it again.
;   Heat.  Touch the A4988 heatsinks at the end.  Hot is normal, too-hot-to-
;   hold is not - that is a Vref that has never been measured.
;   Noise.  A change in the sound partway through is a driver going thermal.
;   Resets.  If the console re-announces 'Grbl 1.1h', note the lap number.
;
; For a visible record, tape the pen down before starting.  All 58 laps draw
; over each other, so a clean run is one sharp square and any drift shows as
; a thickening or a smear.  The pen stays taped for the whole run - do not
; add M3 commands to this file.
G21
G90
G94
G91
G1 F500 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 10 of 58  -  ~1:42 elapsed
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 20 of 58  -  ~3:25 elapsed
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 30 of 58  -  ~5:08 elapsed
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 40 of 58  -  ~6:50 elapsed
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 50 of 58  -  ~8:33 elapsed
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
G1 X-20 Y0
G1 X0 Y20
G1 X20 Y0
G1 X0 Y-20
; lap 58 of 58  -  ~9:55 elapsed
G90
