#!/usr/bin/env python3
"""plot2.py - GRBL sender for the pen plotter.

Homes first, then streams, all in one connection - which matters because opening
the serial port resets the Arduino and throws away the previous home.

    python3 plot2.py --list                      list serial ports
    python3 plot2.py drawing.gcode               home, then plot
    python3 plot2.py --no-home drawing.gcode     stream without homing
    python3 plot2.py --send '$$'                 send raw commands (repeatable)
    python3 plot2.py --jog X10 --jog Y-5         relative jog, mm
    python3 plot2.py --pen up                    pen up / down
    python3 plot2.py --status                    just report where it is

Port defaults to PORT below; override with --port.
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
RX_BUF = 128          # GRBL's serial receive buffer
PEN_UP, PEN_DOWN = 120, 60

STATE_RE = re.compile(r"<([A-Za-z]+)[|>]")


class Grbl:
    def __init__(self, port, baud, verbose=True):
        self.v = verbose
        self.last_status = ""
        print("Opening %s (this resets the Arduino) ..." % port)
        self.ser = serial.Serial(port, baud, timeout=0.2)
        time.sleep(2.0)                     # ride out the reset and banner
        self.ser.reset_input_buffer()

    def close(self):
        self.ser.close()

    # ---- low level -------------------------------------------------------
    def _readline(self):
        return self.ser.readline().decode(errors="replace").strip()

    def _write(self, s):
        self.ser.write(s.encode())
        self.ser.flush()

    def status(self, timeout=2.0):
        """Send ? and return the state word, e.g. 'Idle'."""
        self._write("?")
        end = time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if line.startswith("<"):
                self.last_status = line
                m = STATE_RE.match(line)
                return m.group(1) if m else "?"
        return None

    def command(self, cmd, timeout=15.0):
        """Send one line, wait for ok/error. Returns list of reply lines."""
        self._write(cmd + "\n")
        replies, end = [], time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if not line:
                continue
            if line.startswith("Grbl ") and "for help" in line:
                raise RuntimeError("GRBL RESET mid-command (brownout?)")
            if line == "ok":
                return replies
            if line.startswith("error") or line.startswith("ALARM"):
                replies.append(line)
                return replies
            replies.append(line)
        raise RuntimeError("no reply to %r within %ss" % (cmd, timeout))

    def wait_idle(self, timeout=300.0):
        """Block until GRBL reports Idle. Homing can take a while - that's fine."""
        end, seen = time.time() + timeout, None
        while time.time() < end:
            st = self.status()
            if st != seen:
                if self.v and st:
                    print("   state: %s" % st)
                seen = st
            if st == "Idle":
                return True
            if st == "Alarm":
                print("   !! ALARM -- %s" % self.last_status)
                return False
            time.sleep(0.3)
        print("   !! still not Idle after %ss" % timeout)
        return False

    def work_offset(self):
        """Return the G54 offset as a tuple, or None if it can't be read."""
        for line in self.command("$#"):
            if line.startswith("[G54:"):
                nums = line[5:].rstrip("]").split(",")
                try:
                    return tuple(float(n) for n in nums)
                except ValueError:
                    return None
        return None

    # ---- high level ------------------------------------------------------
    def home(self):
        print("Homing ($H) -- X first, then Y. This takes a while.")
        self._write("$H\n")
        end = time.time() + 300
        while time.time() < end:                 # $H replies 'ok' only when done
            line = self._readline()
            if not line:
                continue
            if line == "ok":
                print("   homed.")
                return True
            if line.startswith("ALARM") or line.startswith("error"):
                print("   !! %s" % line)
                return False
            if line.startswith("Grbl ") and "for help" in line:
                print("   !! GRBL RESET during homing")
                return False
        print("   !! homing timed out")
        return False

    def stream(self, lines):
        """Character-counting flow control: keep GRBL's 128-byte buffer full."""
        pending, idx, acked, errors = [], 0, 0, 0
        total = len(lines)
        while acked < total:
            while idx < total:
                nxt = lines[idx] + "\n"
                if len(nxt) >= RX_BUF:
                    sys.exit("line %d is too long for GRBL: %r" % (idx + 1, lines[idx]))
                if sum(pending) + len(nxt) >= RX_BUF:
                    break
                self._write(nxt)
                pending.append(len(nxt))
                idx += 1
            line = self._readline()
            if not line:
                continue
            if line == "ok":
                pending.pop(0); acked += 1
                if acked % 25 == 0 or acked == total:
                    print("   %d/%d" % (acked, total), end="\r", flush=True)
            elif line.startswith("error") or line.startswith("ALARM"):
                errors += 1
                print("\n   !! %s  on: %s" % (line, lines[acked]))
                pending.pop(0); acked += 1
                if line.startswith("ALARM"):
                    print("   stopping.")
                    return False
            elif line.startswith("Grbl ") and "for help" in line:
                print("\n   !! GRBL RESET mid-stream at line %d (brownout)" % (acked + 1))
                return False
            # anything else ([MSG:..], <status>) is informational
        print()
        return errors == 0


def load(path):
    """Read the whole file, strip comments and blanks."""
    with open(path) as f:
        raw = f.read()
    out = []
    for ln in raw.splitlines():
        ln = re.sub(r"\(.*?\)", "", ln)         # (parenthesised comments)
        ln = ln.split(";")[0].strip()           # ;line comments
        if ln:
            out.append(ln)
    if not out:
        sys.exit("%s has no G-code in it (empty or not downloaded?)" % path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--port", default=PORT)
    ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--no-home", action="store_true", help="skip homing")
    ap.add_argument("--send", action="append", default=[], help="raw command (repeatable)")
    ap.add_argument("--jog", action="append", default=[], help="relative jog, e.g. X10")
    ap.add_argument("--pen", choices=["up", "down"])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--force", action="store_true", help="skip the work-zero safety check")
    ap.add_argument("--unlock", action="store_true", help="send $X")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            print("%-30s %s" % (p.device, p.description))
        return

    lines = load(args.file) if args.file else None
    if lines:
        print("Loaded %s: %d G-code lines." % (args.file, len(lines)))

    g = Grbl(args.port, args.baud)
    ok = True
    try:
        print("Start state: %s" % g.status())

        if args.unlock:
            g.command("$X")
            print("Unlocked.")

        # Home unless told not to. Anything positional depends on it.
        needs_home = (lines or args.jog or args.pen) and not args.no_home
        if needs_home and not args.status:
            if not g.home():
                ok = False
            else:
                g.wait_idle()

        for c in args.send:
            print("%s ->" % c)
            for r in g.command(c):
                print("   %s" % r)

        for j in args.jog:
            g.command("$J=G91 G21 %s F1500" % j)
            g.wait_idle(60)
            print("jogged %s" % j)

        if args.pen:
            s = PEN_UP if args.pen == "up" else PEN_DOWN
            g.command("M3 S%d" % s)
            g.command("G4 P0.3")
            print("pen %s (S%d)" % (args.pen, s))

        if ok and lines and not args.force:
            wco = g.work_offset()
            if wco is not None and all(abs(v) < 0.001 for v in wco):
                print("")
                print("!! REFUSING TO RUN: work offset (G54) is zero.")
                print("!! X0 Y0 in your file would mean MACHINE zero -- the home")
                print("!! corner -- so the gantry would drive into its end stops.")
                print("!! Set a work zero first, e.g.:")
                print("!!     python3 plot2.py --no-home --send 'G10 L2 P1 X-303 Y-107'")
                print("!! Then re-run. (--force overrides this check.)")
                ok = False
            elif wco:
                print("Work zero (G54): X%.1f Y%.1f" % (wco[0], wco[1]))

        if ok and lines:
            print("Streaming %d lines ..." % len(lines))
            ok = g.stream(lines)
            if ok:
                print("All lines acknowledged. Waiting for motion to finish ...")
                g.wait_idle()
                print("Finished.")

        g.status()
        print("Position: %s" % g.last_status)
    except RuntimeError as e:
        print("!! %s" % e)
        ok = False
    except KeyboardInterrupt:
        print("\n!! interrupted -- sending feed hold")
        g._write("!")
        ok = False
    finally:
        g.close()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
