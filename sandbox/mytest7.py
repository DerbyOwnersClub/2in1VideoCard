#!/usr/bin/env python3.12
###################################################################################
#
# Source:
# https://github.com/DerbyOwnersClub/2in1VideoCard
#
#
# Purpose:
# To test available video resources with gstream 
# and provide the results on the console and in a log file named
# video_test.log.
#
# Summary: 
# Video devices are enumerated and cycled thru with different tests.
# Video is attempted to be displayed in different formats discovered 
# and the operator is prompted to answer y or n if video is seen on the screen.
# There is a log file written during execution and a summary written to the console
# at the end of execution.
#
#
# Requirements:
# Unix based operating system.
# Python 3.12
# Hardware to capture video
# Software - Gstream installation
#
# 
#----------------------------------------------------------------------------------------------------------------------------------- 
# Troubleshoot Table:
#----------------------------------------------------------------------------------------------------------------------------------
# Message										| Action
#----------------------------------------------------------------------------------------------------------------------------------
# Permission denied							 | chmod +x SEGADOC2in1Video.py
# /dev/video#: Device or resource busy| another process has it locked. 
#														 | fuser /dev/video#
#														 | kill 7 digit process. e.g. 1423631
#														 |
# NO VALID VIDEO                            | make sure the devices are plugged in and turned on.
#                                                       | if using an upscaler or video converter, validate the device is plugged in and turned on.
#                                                       | Use an external monitor to validate the source.
#
#
#----------------------------------------------------------------------------------------------------------------------------------
#
#----------------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------
# Date         | Author                            			| Description
#----------------------------------------------------------------------------------------------------------------------------------
# 20250912  | TedmondFromRedmond  (TFR)	| Maker
#
#
#----------------------------------------------------------------------------------------------------------------------------------
#
###################################################################################

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

def sort_video_devices(devices):
    """Sort /dev/video* devices numerically (video0, video1, …)."""
    return sorted(devices, key=lambda x: int(re.search(r'\d+$', x).group()))

# ---------------- Test Runners ---------------- #

def run_ffplay(device, res="1280x720", fps=30, duration=5, input_format="mjpeg"):
    """
    Run ffplay for `duration` seconds, then close.
    Suppresses console output (errors/warnings).
    """
    cmd = [
        "ffplay", "-hide_banner", "-loglevel", "error",
        "-f", "v4l2",
        "-input_format", input_format,
        "-framerate", str(fps),
        "-video_size", res,
        device
    ]
    proc = subprocess.Popen(
        cmd, preexec_fn=os.setsid,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        time.sleep(duration)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()

def run_gstreamer(device, pipeline, duration=5):
    """
    Run a gstreamer pipeline for `duration` seconds, then close.
    Suppresses console output (errors/warnings).
    """
    cmd = ["gst-launch-1.0"] + pipeline
    proc = subprocess.Popen(
        cmd, preexec_fn=os.setsid,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        time.sleep(duration)
    finally:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()

# ---------------- Main Workflow ---------------- #

def main():
    now = datetime.datetime.now()
#     logfile = f"video_test_{now.strftime('%Y%m%d-%H%M')}.log"
    logfile = f"video_test_log.txt"

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

        # Save device format info to log only
        log("--- v4l2-ctl formats ---", logfile)
        subprocess.run(
            ["v4l2-ctl", f"--device={dev}", "--list-formats-ext"],
            stdout=open(logfile, "a"), stderr=subprocess.STDOUT
        )

        # ---- Device Summary ----
        if device_worked:
            report.append(f"Device {dev} → ✅ WORKING")
        else:
            report.append(f"Device {dev} → ❌ NO VALID VIDEO")
        log("", logfile)

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


    # ---- Final summary ----
    log("=== Troubleshoot Complete. Log saved to " + logfile, logfile)
    log("\n=== Report Summary ===", logfile)
    for line in report:
        log(line, logfile)

    print("\n".join(report))

if __name__ == "__main__":
    main()
