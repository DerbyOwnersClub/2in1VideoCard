#!/usr/bin/env python3.12
###################################################################################
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
# If one is unable to get the video working, review the log file and use the 
# Troubleshoot Table below.
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
# Date         | Author                            			                                       | Description
#----------------------------------------------------------------------------------------------------------------------------------
# 20250913  | TFR (TedmondFromRedmond@gmail.com)                        | Maker
#
#
#----------------------------------------------------------------------------------------------------------------------------------
#
# Usage:
# Python DiscoverWorkingVideo.py
#
#
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
import csv

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

def ask_yes_no(prompt):
    """Ask the operator a y/n question."""
    print(f"{prompt} (y/n): ", end="", flush=True)
    ch = getch().lower()
    print()
    return ch == "y"

def sort_video_devices(devices):
    """Sort /dev/video* devices numerically (video0, video1, …)."""
    return sorted(devices, key=lambda x: int(re.search(r'\d+$', x).group()))

# ---------------- Test Runners ---------------- #

def run_ffplay(device, res="1280x720", fps=30, duration=5, input_format="mjpeg"):
    """Run ffplay for N seconds, suppressing output."""
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
    """Run a gstreamer pipeline for N seconds, suppressing output."""
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
#    csvfile = f"video_test_{now.strftime('%Y%m%d-%H%M')}.csv"
    csvfile = f"video_test.csv"

    # Open CSV file with headers
    with open(csvfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "device", "test_type", "resolution", "fps", "format", "operator_response"])

        devices = sort_video_devices(glob.glob("/dev/video*"))
        if not devices:
            print("No /dev/video* devices found.")
            sys.exit(1)

        report = []

        for dev in devices:
            print(f"\n===== Device: {dev} =====")

            device_worked = False

            # ---- MJPEG tests ----
            for res in ["1920x1080", "1280x720", "640x480"]:
                for fps in [60, 30]:
                    run_ffplay(dev, res, fps, duration=5, input_format="mjpeg")
                    if ask_yes_no(f"Did you see video for {dev} at {res} MJPEG {fps}fps?"):
                        device_worked = True
                        writer.writerow([datetime.datetime.now().isoformat(), dev, "ffplay", res, fps, "MJPEG", "YES"])
                    else:
                        writer.writerow([datetime.datetime.now().isoformat(), dev, "ffplay", res, fps, "MJPEG", "NO"])

            # ---- YUYV test ----
            run_ffplay(dev, "640x480", 10, duration=5, input_format="yuyv422")
            if ask_yes_no(f"Did you see video for {dev} at 640x480 YUYV 10fps?"):
                device_worked = True
                writer.writerow([datetime.datetime.now().isoformat(), dev, "ffplay", "640x480", 10, "YUYV", "YES"])
            else:
                writer.writerow([datetime.datetime.now().isoformat(), dev, "ffplay", "640x480", 10, "YUYV", "NO"])

            # ---- GStreamer JPEGDEC test ----
            run_gstreamer(dev, ["v4l2src", f"device={dev}", "!", "jpegdec", "!", "fakesink"], duration=5)
            if ask_yes_no(f"Did you see video for {dev} (GStreamer JPEGDEC)?"):
                device_worked = True
                writer.writerow([datetime.datetime.now().isoformat(), dev, "gstreamer", "-", "-", "JPEGDEC", "YES"])
            else:
                writer.writerow([datetime.datetime.now().isoformat(), dev, "gstreamer", "-", "-", "JPEGDEC", "NO"])

            # ---- Device Summary ----
            if device_worked:
                report.append(f"Device {dev} → ✅ WORKING")
            else:
                report.append(f"Device {dev} → ❌ NO VALID VIDEO")

    # ---- Final summary ----
    print("\n=== Troubleshoot Complete. CSV saved to " + csvfile + " ===")
    print("\n=== Report Summary ===")
    print("\n".join(report))

if __name__ == "__main__":
    main()
