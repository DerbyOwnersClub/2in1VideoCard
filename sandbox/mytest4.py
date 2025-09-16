#!/usr/bin/env python3
import glob
import subprocess
import sys
import datetime
import os
import signal
import time
import termios
import tty
import re

# ---------------- Utilities ---------------- #

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

def ask_yes_no(prompt):
    print(f"{prompt} (y/n): ", end="", flush=True)
    ch = getch().lower()
    print()
    return ch == "y"

def run_ffplay(device="/dev/video2", res="1280x720", fps=30, duration=5, input_format="mjpeg"):
    """
    Launch ffplay to test a video mode.
    Shows video in a window, runs for `duration` seconds, then closes.
    """
    cmd = [
        "ffplay", "-hide_banner", "-loglevel", "error",
        "-f", "v4l2",
        "-input_format", input_format,
        "-framerate", str(fps),
        "-video_size", res,
        device
    ]
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
    try:
        time.sleep(duration)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()

def run_gstreamer(device, pipeline, duration=5):
    """
    Run a gstreamer pipeline for `duration` seconds, then kill it.
    Example pipeline: ["v4l2src", f"device={device}", "!", "jpegdec", "!", "fakesink"]
    """
    cmd = ["gst-launch-1.0"] + pipeline
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
    try:
        time.sleep(duration)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()

def sort_video_devices(devices):
    """Sort /dev/video* devices numerically (video0, video1, video2…)."""
    return sorted(devices, key=lambda x: int(re.search(r'\d+$', x).group()))

# ---------------- Main Workflow ---------------- #

def main():
    now = datetime.datetime.now()
    logfile = f"video_test_{now.strftime('%Y%m%d-%H%M')}.log"

    log("=== Video Troubleshoot Log ===", logfile)
    log(f"Timestamp: {now.isoformat()}", logfile)
    log("", logfile)

    devices = sort_video_devices(glob.glob("/dev/video*"))
    if not devices:
        log("No /dev/video* devices found.", logfile)
        sys.exit(1)

    report = []

    for dev in devices:
        log(f"===== Device: {dev} =====", logfile)
        log("", logfile)

        # List device capabilities
        log("--- v4l2-ctl formats ---", logfile)
        subprocess.run(
            ["v4l2-ctl", f"--device={dev}", "--list-formats-ext"],
            stdout=open(logfile, "a"), stderr=subprocess.STDOUT
        )

        device_worked = False

        # ---- MJPEG tests ----
        for res in ["1920x1080", "1280x720", "640x480"]:
            for fps in [60, 30]:
                log(f"--- ffplay MJPEG {res} {fps}fps ---", logfile)
                run_ffplay(dev, res, fps, duration=5, input_format="mjpeg")
                if ask_yes_no(f"Did you see video for {dev} at {res} MJPEG {fps}fps?"):
                    device_worked = True
                    log(f"{dev} at {res} MJPEG {fps}fps operator answered YES", logfile)

        # ---- YUYV test ----
        log("--- ffplay YUYV 640x480 10fps ---", logfile)
        run_ffplay(dev, "640x480", 10, duration=5, input_format="yuyv422")
        if ask_yes_no(f"Did you see video for {dev} at 640x480 YUYV 10fps?"):
            device_worked = True
            log(f"{dev} at 640x480 YUYV 10fps operator answered YES", logfile)

        # ---- GStreamer JPEGDEC test ----
        log("--- GStreamer JPEGDEC test ---", logfile)
        run_gstreamer(dev, ["v4l2src", f"device={dev}", "!", "jpegdec", "!", "fakesink"], duration=5)
        if ask_yes_no(f"Did you see video for {dev} (GStreamer JPEGDEC)?"):
            device_worked = True
            log(f"{dev} GStreamer JPEGDEC operator answered YES", logfile)

        # ---- Report summary for device ----
        if device_worked:
            report.append(f"Device {dev} → ✅ WORKING")
        else:
            report.append(f"Device {dev} → ❌ NO VALID VIDEO")

        log("", logfile)

    # ---- Final summary ----
    log("=== Troubleshoot Complete. Log saved to " + logfile, logfile)
    log("\n=== Report Summary ===", logfile)
    for line in report:
        log(line, logfile)

    print("\n".join(report))

if __name__ == "__main__":
    main()
