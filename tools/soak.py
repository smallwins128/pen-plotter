#!/usr/bin/env python3
"""soak.py - run the plotter in a loop until something breaks, and time it.

Built for one question: how long does this machine survive servo-after-move
before the controller resets?  It runs one cycle over and over, prints a live
elapsed clock, and when it dies it tells you exactly how long it lasted, how
many cycles it completed, and what was in flight at the time.

Three arms, so you can isolate the variable (FINDINGS.md section 7 rules out
motion alone and servo alone; --mode lets you re-confirm that on new hardware):

    --mode both      Y move, then pen down, Y move back, pen up   [default]
    --mode motion    Y moves only, servo never commanded          (control)
    --mode servo     pen up/down only, no motion                  (control)

Usage:

    python3 soak.py                          # both, forever, until it dies
    python3 soak.py --mode motion            # control arm
    python3 soak.py --minutes 10             # stop cleanly after 10 min
    python3 soak.py --cycles 50              # stop cleanly after 50 cycles
    python3 soak.py --dist 60 --up 120 --down 60

Ctrl-C stops it and still prints the summary.  Every run writes a timestamped
log file you can paste back verbatim.

NO ENDSTOPS REQUIRED - this tool never homes.  It moves relative only.
Requires: pip3 install pyserial
"""

import argparse, datetime, re, sys, time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    sys.exit("pyserial not installed.  Run:  pip3 install pyserial")

PORT = "/dev/cu.usbserial-A5069RR4"
BAUD = 115200
PEN_UP, PEN_DOWN = 120, 60

STATE_RE = re.compile(r"<([A-Za-z]+)[|>]")


class Died(Exception):
    """The machine stopped being a machine we can talk to."""
    def __init__(self, kind, detail, during):
        super().__init__("%s during %r: %s" % (kind, during, detail))
        self.kind, self.detail, self.during = kind, detail, during


class Grbl:
    def __init__(self, port, baud, log):
        self.log = log
        self.last_status = ""
        self.rx_tail = []           # last few lines, for the post-mortem
        print("Opening %s (this resets the Arduino) ..." % port)
        self.ser = serial.Serial(port, baud, timeout=0.2)
        time.sleep(2.0)             # ride out the reset and the banner
        self.ser.reset_input_buffer()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def _readline(self):
        line = self.ser.readline().decode(errors="replace").strip()
        if line:
            self.rx_tail.append(line)
            del self.rx_tail[:-20]
            self.log.write("    RX  %s\n" % line)
        return line

    def _write(self, s):
        if s.strip():
            self.log.write("TX      %s\n" % s.strip())
        self.ser.write(s.encode())
        self.ser.flush()

    def _check_fatal(self, line, during):
        """Raise if this line means the controller is gone or refusing."""
        if line.startswith("Grbl ") and "for help" in line:
            raise Died("CONTROLLER RESET", line, during)
        if line.startswith("ALARM"):
            raise Died("ALARM", line, during)

    def command(self, cmd, timeout=60.0):
        """Send one line, wait for its ok.  Lockstep - no buffering."""
        self._write(cmd + "\n")
        replies, end = [], time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if not line:
                continue
            self._check_fatal(line, cmd)
            if line == "ok":
                return replies
            if line.startswith("error"):
                raise Died("ERROR", line, cmd)
            replies.append(line)
        raise Died("TIMEOUT", "no reply within %.0fs" % timeout, cmd)

    def status(self, timeout=3.0):
        self._write("?")
        end = time.time() + timeout
        while time.time() < end:
            line = self._readline()
            if not line:
                continue
            if line.startswith("Grbl ") and "for help" in line:
                raise Died("CONTROLLER RESET", line, "?")
            if line.startswith("<"):
                self.last_status = line
                m = STATE_RE.match(line)
                return m.group(1) if m else "?"
        return None

    def wait_idle(self, timeout=120.0, during="move"):
        end = time.time() + timeout
        while time.time() < end:
            st = self.status()
            if st == "Idle":
                return
            if st == "Alarm":
                raise Died("ALARM", self.last_status, during)
            time.sleep(0.15)
        raise Died("STUCK", "never returned to Idle within %.0fs" % timeout, during)


def hms(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))


def preflight(g, args):
    """Read the machine's own account of itself into the log, and refuse to run
    into a configuration that will just alarm instantly."""
    print("")
    print("$I ->")
    for line in g.command("$I"):
        print("   %s" % line)

    print("$$ ->")
    settings = {}
    for line in g.command("$$"):
        print("   %s" % line)
        m = re.match(r"\$(\d+)=([\d.]+)", line)
        if m:
            settings[int(m.group(1))] = float(m.group(2))

    if settings.get(21) == 1:
        sys.exit("\n!! $21=1 (hard limits ON) and your endstops are not wired.\n"
                 "!! The floating pins read as triggered and this will ALARM on the\n"
                 "!! first move. Set $21=0 (PSU OFF, USB only) and re-run.")
    if settings.get(20) == 1:
        print("\n!! $20=1 (soft limits ON) and the machine is not homed.")
        print("!! Moves may throw ALARM:2 - that is a settings artefact, NOT the")
        print("!! reset you are hunting. Consider $20=0 for this test.")

    st = g.status()
    print("\nState: %s" % st)
    print("Status line: %s" % g.last_status)
    if "Pn:" in g.last_status:
        print("   ('Pn:' with endstops unwired is EXPECTED - $5=1 inverts floating")
        print("    pins so they read as triggered. Harmless while $21=0.)")
    return st


def softstart(g, up):
    """FINDINGS.md section 6 - the servo is limp until the first M3, and jumping
    straight to an extreme from limp is the largest current step it ever makes."""
    print("Soft-starting the servo (S90 -> S%d) ..." % up)
    step = 10 if up > 90 else -10
    g.command("M3 S90")
    g.command("G4 P0.50")
    for s in range(90 + step, up, step):
        g.command("M3 S%d" % s)
        g.command("G4 P0.30")
    g.command("M3 S%d" % up)
    g.command("G4 P0.30")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=PORT)
    ap.add_argument("--baud", type=int, default=BAUD)
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--mode", choices=["both", "motion", "servo"], default="both")
    ap.add_argument("--axis", choices=["X", "Y"], default="Y",
                    help="which axis to move (default Y). Only this axis is ever "
                         "commanded - if another one turns, that is a wiring fault.")
    ap.add_argument("--dist", type=float, default=40.0, help="move distance, mm (default 40)")
    ap.add_argument("--up", type=int, default=PEN_UP)
    ap.add_argument("--down", type=int, default=PEN_DOWN)
    ap.add_argument("--dwell", type=float, default=0.30, help="pause after each pen command")
    ap.add_argument("--cycles", type=int, help="stop cleanly after N cycles")
    ap.add_argument("--minutes", type=float, help="stop cleanly after N minutes")
    ap.add_argument("--no-settle", action="store_true",
                    help="do not wait for Idle between move and pen (buffered, "
                         "more like a real plot; cycle count runs ahead of motion)")
    ap.add_argument("--no-softstart", action="store_true",
                    help="skip the staged servo wake - tests the harsh first-M3 case")
    args = ap.parse_args()

    if args.list:
        for p in list_ports.comports():
            print("%-30s %s" % (p.device, p.description))
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    logname = "soak-%s-%s.log" % (args.mode, stamp)
    log = open(logname, "w", buffering=1)
    log.write("soak.py %s  mode=%s axis=%s dist=%s up=%s down=%s settle=%s softstart=%s\n\n"
              % (stamp, args.mode, args.axis, args.dist, args.up, args.down,
                 not args.no_settle, not args.no_softstart))

    print("=" * 68)
    print("  SOAK TEST - mode: %s" % args.mode)
    print("=" * 68)
    print("  No endstops needed: this never homes and moves RELATIVE only.")
    print("  Before you start:")
    print("    - park the gantry near the MIDDLE of its %s travel by hand" % args.axis)
    print("    - keep a hand on the mains switch")
    print("    - %.0f mm of %s clearance is needed in each direction"
          % (args.dist, args.axis))
    print("  Ctrl-C stops it and still prints the summary.")
    print("  Log: %s" % logname)
    print("=" * 68)

    g = Grbl(args.port, args.baud, log)
    cycles = 0
    t0 = None
    death = None

    try:
        preflight(g, args)
        print("\nUnlocking ($X - $22=1 makes GRBL boot into Alarm) ...")
        g.command("$X")
        g.command("G21")
        g.command("G90")
        g.command("G94")
        g.command("G91")                       # everything below is relative

        if args.mode != "motion" and not args.no_softstart:
            softstart(g, args.up)

        print("\nRunning. Live line below updates every cycle.\n")
        t0 = time.time()
        deadline = t0 + args.minutes * 60 if args.minutes else None

        while True:
            if args.cycles and cycles >= args.cycles:
                break
            if deadline and time.time() > deadline:
                break

            log.write("\n--- cycle %d  t=%s ---\n" % (cycles + 1, hms(time.time() - t0)))

            if args.mode in ("both", "motion"):
                g.command("G0 %s-%.3f" % (args.axis, args.dist))
                if not args.no_settle:
                    g.wait_idle(during="%s-%.3f" % (args.axis, args.dist))

            if args.mode in ("both", "servo"):
                g.command("M3 S%d" % args.down)
                g.command("G4 P%.2f" % args.dwell)

            if args.mode in ("both", "motion"):
                g.command("G0 %s%.3f" % (args.axis, args.dist))
                if not args.no_settle:
                    g.wait_idle(during="%s+%.3f" % (args.axis, args.dist))

            if args.mode in ("both", "servo"):
                g.command("M3 S%d" % args.up)
                g.command("G4 P%.2f" % args.dwell)

            cycles += 1
            print("  cycle %-5d  elapsed %-10s  (%.1f s/cycle)"
                  % (cycles, hms(time.time() - t0), (time.time() - t0) / cycles),
                  end="\r", flush=True)

    except Died as e:
        death = e
    except KeyboardInterrupt:
        print("\n\n  interrupted - sending feed hold")
        try:
            g._write("!")
        except Exception:
            pass
    except Exception as e:                      # serial dropped, USB yanked, etc.
        death = Died("SERIAL FAILURE", repr(e), "unknown")

    elapsed = (time.time() - t0) if t0 else 0.0

    summary = []
    summary.append("")
    summary.append("=" * 68)
    if death:
        summary.append("  DIED: %s" % death.kind)
        summary.append("=" * 68)
        summary.append("  survived      : %s  (%.1f s)" % (hms(elapsed), elapsed))
        summary.append("  cycles done   : %d" % cycles)
        summary.append("  in flight     : %s" % death.during)
        summary.append("  what came back: %s" % death.detail)
    else:
        summary.append("  SURVIVED - stopped on request, not on failure")
        summary.append("=" * 68)
        summary.append("  ran for       : %s  (%.1f s)" % (hms(elapsed), elapsed))
        summary.append("  cycles done   : %d" % cycles)
    if cycles:
        summary.append("  per cycle     : %.1f s" % (elapsed / cycles))
    summary.append("  mode          : %s   axis %s   dist %.0f mm   S%d/%d"
                   % (args.mode, args.axis, args.dist, args.up, args.down))
    summary.append("")
    summary.append("  last 20 lines from the controller:")
    for line in g.rx_tail:
        summary.append("    %s" % line)
    summary.append("")
    summary.append("  full log: %s" % logname)
    summary.append("=" * 68)

    text = "\n".join(summary)
    print("\n" + text)
    log.write("\n" + text + "\n")
    log.close()
    g.close()
    sys.exit(1 if death else 0)


if __name__ == "__main__":
    main()
