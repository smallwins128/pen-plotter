#!/usr/bin/env python3
"""Find the pen-up and pen-down S values for a servo on D11.

Interactive. Sends `M3 S<n>` followed by a dwell, so the pen change is planner-synced
exactly the way it will be inside a real plot.

    python3 tools/servo_sweep.py --port /dev/cu.usbserial-A5069RR4

Keys:
    u / <up arrow>     raise S by one PWM count (about 6 units of S)
    d / <down arrow>   lower S by one PWM count
    <number>           jump straight to that S value
    +N / -N            nudge by N
    q                  park at the current value and quit

Resolution note: with the recommended firmware ($30=180, PWM range 8..39) one PWM count
is 64 us of pulse width and about 6 units of S. Steps smaller than that do nothing.

Requires: pip3 install pyserial
"""

import argparse
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed.  pip3 install pyserial")

STEP = 6          # one PWM count at $30=180 over a 31-count range
DWELL = 0.30      # seconds, matches the G4 P in the generated files


def send(ser, line, quiet=False):
    ser.write((line + "\n").encode())
    ser.flush()
    replies = []
    deadline = time.time() + 5.0
    while time.time() < deadline:
        raw = ser.readline().decode(errors="replace").strip()
        if not raw:
            continue
        replies.append(raw)
        if raw == "ok" or raw.startswith("error") or raw.startswith("ALARM"):
            break
    if not quiet:
        for r in replies:
            if r != "ok":
                print("   <- %s" % r)
    return replies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port; omit to list what is available")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--start", type=int, default=120,
                help="starting S value (default 120 = pen down, the safe resting end)")
    args = ap.parse_args()

    if not args.port:
        for p in list_ports.comports():
            print("%-28s %s" % (p.device, p.description))
        return

    print("Opening %s -- this resets the Arduino." % args.port)
    ser = serial.Serial(args.port, args.baud, timeout=0.25)
    time.sleep(2.0)                      # wait out the reset and the GRBL banner
    ser.reset_input_buffer()

    send(ser, "$I")
    # GRBL boots into the Alarm state whenever $22=1 (homing enabled), and in Alarm
    # it refuses G-code with error:9 -- M3 included. Without this $X the sweep runs
    # happily, prints every S value, and never moves the servo at all.
    send(ser, "$X")
    send(ser, "G21")
    send(ser, "G90")

    s = max(0, min(180, args.start))
    print("\nStarting at S%d.  u/d = +/-%d, a number jumps, q quits.\n" % (s, STEP))

    while True:
        replies = send(ser, "M3 S%d" % s, quiet=True)
        send(ser, "G4 P%.2f" % DWELL, quiet=True)
        bad = [r for r in replies if r.startswith(("error", "ALARM"))]
        if bad:
            print("  !! %s -- the servo command was REFUSED. The pen has not moved." % bad[0])
            if bad[0].startswith("error:9"):
                print("  !! error:9 is GRBL's 'locked out during alarm'. The $X on connect")
                print("  !! did not take. Quit with q and check $22 / the alarm state.")
        pwm = min(39, int(s * 31 / 180) + 8) if s > 0 else 0
        print("S%-4d  pwm=%-3s pulse=%s"
              % (s, pwm if pwm else "off", ("%d us" % (pwm * 64)) if pwm else "NO SIGNAL (servo limp)"))

        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            cmd = "q"

        if cmd in ("q", "quit", "exit"):
            break
        elif cmd in ("u", "up", ""):
            s = min(180, s + STEP)
        elif cmd in ("d", "down"):
            s = max(0, s - STEP)
        elif cmd.startswith(("+", "-")):
            try:
                s = max(0, min(180, s + int(cmd)))
            except ValueError:
                print("  ?")
        else:
            try:
                s = max(0, min(180, int(cmd)))
            except ValueError:
                print("  ? u / d / <number> / +N / -N / q")

    print("\nParked at S%d.  Put your two values into the test files and your generator:" % s)
    print("    pen up   -> M3 S<up>   + G4 P0.30")
    print("    pen down -> M3 S<down> + G4 P0.30")
    ser.close()


if __name__ == "__main__":
    main()
