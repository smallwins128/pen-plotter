#!/usr/bin/env python3
"""servo_check.py - verify the pen servo after a wiring change, ending PEN UP.

Runs a staged ladder of growing swings and stops the moment the controller
resets, telling you which stage it got to. Nothing here moves a motor.

    stage 1  energise at centre from limp   <- the largest current step there is
    stage 2  +/- 20% of your range
    stage 3  +/- 50%
    stage 4  full range, once
    stage 5  full range, three cycles
    park     pen UP, and hold it there

Why a ladder: FINDINGS.md section 6 - the servo is limp until the first M3, and
going straight to an extreme from limp is the biggest current step it ever makes.
If the supply is marginal this dies at stage 1 and you learn that without having
thrashed the mechanism.

    python3 servo_check.py                    # ladder, park at pen up, hold
    python3 servo_check.py --up 120 --down 60
    python3 servo_check.py --park-only        # skip the ladder, just go to pen up
    python3 servo_check.py --no-hold          # do not wait for Enter at the end

Never sends M5 or S0: both disconnect the PWM pin and the servo goes limp, which
drops the pen (FIRMWARE_SERVO.md section 7). Pen up is M3 S<up>, always.

Requires: pip3 install pyserial
"""

import argparse, re, sys, time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed.  Run:  pip3 install pyserial")

PORT = "/dev/cu.usbserial-A5069RR4"
BAUD = 115200
PEN_UP, PEN_DOWN = 120, 60
DWELL = 0.30

STATE_RE = re.compile(r"<([A-Za-z]+)[|>]")


class Died(Exception):
    def __init__(self, detail, during):
        super().__init__(detail)
        self.detail, self.during = detail, during


class Grbl:
    def __init__(self, port, baud):
        self.last_status = ""
        print("Opening %s (this resets the Arduino) ..." % port)
        self.ser = serial.Serial(port, baud, timeout=0.2)
        time.sleep(2.0)
        self.ser.reset_input_buffer()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def _readline(self):
        return self.ser.readline().decode(errors="replace").strip()

    def _write(self, s):
        self.ser.write(s.encode())
        self.ser.flush()

    def command(self, cmd, timeout=20.0):
        self._write(cmd + "\n")
        replies, end = [], time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if not line:
                continue
            if line.startswith("Grbl ") and "for help" in line:
                raise Died("CONTROLLER RESET - %s" % line, cmd)
            if line == "ok":
                return replies
            if line.startswith("error") or line.startswith("ALARM"):
                raise Died(line, cmd)
            replies.append(line)
        raise Died("no reply within %.0fs" % timeout, cmd)

    def status(self, timeout=3.0):
        self._write("?")
        end = time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if not line:
                continue
            if line.startswith("Grbl ") and "for help" in line:
                raise Died("CONTROLLER RESET - %s" % line, "?")
            if line.startswith("<"):
                self.last_status = line
                m = STATE_RE.match(line)
                return m.group(1) if m else "?"
        return None


def pulse_us(s):
    """The pulse width GRBL will emit, per FIRMWARE_SERVO.md section 6."""
    if s <= 0:
        return None
    return (min(39, int(s * 31 / 180) + 8)) * 64


def goto(g, s, dwell):
    g.command("M3 S%d" % s)
    g.command("G4 P%.2f" % dwell)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=PORT)
    ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--up", type=int, default=PEN_UP, help="pen UP S value (default 120)")
    ap.add_argument("--down", type=int, default=PEN_DOWN, help="pen DOWN S value (default 60)")
    ap.add_argument("--dwell", type=float, default=DWELL)
    ap.add_argument("--park-only", action="store_true", help="skip the ladder, soft-start to pen up")
    ap.add_argument("--no-hold", action="store_true", help="do not wait for Enter before closing")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            print("%-30s %s" % (p.device, p.description))
        return

    if args.up == args.down:
        sys.exit("--up and --down are the same value; nothing to test.")

    centre = (args.up + args.down) // 2
    half = abs(args.up - args.down) / 2.0
    sign = 1 if args.up > args.down else -1

    def at(frac):
        """S values at +/- frac of the range, never outside [down, up]."""
        d = half * frac
        return int(round(centre + sign * d)), int(round(centre - sign * d))

    print("=" * 66)
    print("  SERVO CHECK   pen up S%d (%s us)   pen down S%d (%s us)"
          % (args.up, pulse_us(args.up), args.down, pulse_us(args.down)))
    print("=" * 66)
    print("  No motors are commanded. Watch the pen arm, not the gantry.")
    print("  Final state will be PEN UP, held.")
    print("=" * 66)

    g = Grbl(args.port, args.baud)
    stage = "connect"
    reached = []
    try:
        print("")
        for line in g.command("$I"):
            print("   %s" % line)
        g.command("$X")
        g.command("G21")
        g.command("G90")
        g.command("G94")

        stage = "1: energise at centre (S%d) from limp" % centre
        print("\nstage %s" % stage)
        goto(g, centre, 0.50)
        reached.append(stage)
        print("   survived.")

        if not args.park_only:
            for n, frac in ((2, 0.20), (3, 0.50), (4, 1.00)):
                hi, lo = at(frac)
                stage = "%d: swing S%d / S%d (%.0f%% of range)" % (n, hi, lo, frac * 100)
                print("stage %s" % stage)
                goto(g, hi, args.dwell)
                goto(g, lo, args.dwell)
                goto(g, centre, args.dwell)
                reached.append(stage)
                print("   survived.")

            stage = "5: three full cycles S%d <-> S%d" % (args.up, args.down)
            print("stage %s" % stage)
            for i in range(3):
                goto(g, args.up, args.dwell)
                goto(g, args.down, args.dwell)
                print("   cycle %d/3 ok" % (i + 1))
            reached.append(stage)

        stage = "park at pen up (S%d)" % args.up
        print("\n%s" % stage)
        goto(g, args.up, 0.50)
        reached.append(stage)

        st = g.status()
        print("   state: %s" % st)
        print("   %s" % g.last_status)
        if "A:S" in (g.last_status or ""):
            print("   A:S present - the PWM pin is live and holding S%d." % args.up)
        else:
            print("   !! A:S missing from the status line. The spindle/servo output is")
            print("   !! NOT enabled, so the servo is receiving no pulses and will be limp.")

        print("")
        print("=" * 66)
        print("  PASSED - all %d stages. Servo is parked PEN UP at S%d."
              % (len(reached), args.up))
        print("=" * 66)

        if not args.no_hold:
            print("")
            print("  The port is still open, so GRBL is still holding the pen up.")
            print("  Look at the pen now. It should be lifted and steady - no buzzing.")
            print("")
            try:
                input("  Press Enter to close the port. ")
            except (EOFError, KeyboardInterrupt):
                print("")

    except Died as e:
        print("")
        print("=" * 66)
        print("  FAILED at stage %s" % stage)
        print("=" * 66)
        print("  in flight  : %s" % e.during)
        print("  came back  : %s" % e.detail)
        print("  stages done: %d" % len(reached))
        for s in reached:
            print("     ok  %s" % s)
        print("")
        if stage.startswith("1"):
            print("  Dying at stage 1 means the very first energisation browns out the")
            print("  board - the servo supply cannot deliver the inrush. Check the bulk")
            print("  capacitance is across V+ and GND (not the signal line), and that")
            print("  the buck VOUT- to shield GND bond is fitted. FINDINGS.md sections 2 and 6.")
        else:
            print("  It survived the smaller swings and died on a larger one, so the")
            print("  supply holds at low current and sags under load. That is bulk")
            print("  capacitance at the servo end, or voltage: FINDINGS.md section 6a.")
        g.close()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n  interrupted.")

    print("")
    print("  Closing the port now. On most setups this leaves the board running and")
    print("  the pen stays up; the NEXT time something opens the port, DTR resets the")
    print("  Arduino, the servo goes limp and the pen drops. That is expected, and the")
    print("  cure is the 10 uF RESET-to-GND cap in SETUP.md section 3.5.")
    g.close()


if __name__ == "__main__":
    main()
