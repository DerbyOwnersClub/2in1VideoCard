#!/usr/bin/env python3
import glob
import subprocess
import sys
import datetime
import termios
import tty
import os
import signal
import time

def getch():
    """Read a single keypress (no Enter needed)."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def log(msg, logfile, echo=True):
    if echo:
        print(msg)
    with open(logfile, "a") as f:
        f.write(msg + "\n")

def run_ffplay(cmd_list, logfile, duration=5):
    """
    Run ffplay for a limited duration, logging its output,
    while still showing the video window.
    """
    with open(logfile, "a") as f:
        proc = subprocess.Popen(
            cmd_list,
            stdout=f, stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )
        try:
            time.sleep(duration)
        finally:
            # kill the whole process group after duration
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait()

def ask_yes_no(prompt):
    print(f"{prompt} (y/n): ", end="", flush=True)
    ch = getch().lower()
    print()
    return ch == "y"

def main():
    now = datetime.datetime.now()
    logfile = f"video_test_{now.strftime('%Y%m%d-%H%M')}.log"

    log("=== Video Troubleshoot Log ===", logfile)
    log(f"Timestamp: {now.isoformat()}", logfile)
    log("", logfile)

    devices = glob.glob("/dev/video*")
    if not devices:
        log("No /dev/video* devices found.", logfile)
        sys.exit(1)

    report = []

    for dev in devices:
        log(f"===== Device: {dev} =====", logfile)
        log("", logfile)

        log("--- v4l2-ctl formats ---", logfile)
        subprocess.run(
            ["v4l2-ctl", f"--device={dev}", "--list-formats-ext"],
            stdout=open(logfile, "a"), stderr=subprocess.STDOUT
        )

        device_worked = False

        # MJPEG resolution tests only
        for res in ["1920x1080", "1280x720", "640x480"]:
            for fps in [60, 30]:
                log(f"--- ffplay MJPEG {res} {fps}fps ---", logfile)
                run_ffplay(
                    [
                        "ffplay", "-hide_banner", "-loglevel", "error",
                        "-f", "v4l2", "-input_format", "mjpeg",
                        "-framerate", str(fps),
                        "-video_size", res,
                        dev
                    ],
                    logfile,
                    duration=5
                )
                if ask_yes_no(f"Did you see video for {dev} at {res} MJPEG {fps}fps?"):
                    device_worked = True
                    log(f"{dev} at {res} MJPEG {fps}fps operator answered yes", logfile)

        if device_worked:
            report.append(f"Device {dev} → ✅ WORKING")
        else:
            report.append(f"Device {dev} → ❌ NO VALID VIDEO")

        log("", logfile)

    log("=== Troubleshoot Complete. Log saved to " + logfile, logfile)
    log("\n=== Report Summary ===", logfile)
    for line in report:
        log(line, logfile)

    print("\n".join(report))

if __name__ == "__main__":
    main()
