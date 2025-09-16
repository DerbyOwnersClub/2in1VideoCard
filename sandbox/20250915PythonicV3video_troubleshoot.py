#!/usr/bin/env python3
import glob
import subprocess
import sys
import datetime
import termios
import tty

# ---------- Utilities ----------

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

def run_command(cmd, logfile, timeout=5):
    try:
        subprocess.run(
            cmd, shell=True, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    except Exception as e:
        with open(logfile, "a") as f:
            f.write(f"[ERROR] {cmd}: {e}\n")

def ask_yes_no(prompt):
    print(f"{prompt} (y/n): ", end="", flush=True)
    ch = getch().lower()
    print()  # newline after keypress
    return ch == "y"

# ---------- Main Workflow ----------

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

        # List capabilities
        log("--- v4l2-ctl formats ---", logfile)
        run_command(f"v4l2-ctl --device={dev} --list-formats-ext", logfile)

        device_worked = False

        # ----- MJPEG resolution tests only -----
        for res in ["1920x1080", "1280x720", "640x480"]:
            for fps in [60, 30]:
                log(f"--- ffplay MJPEG {res} {fps}fps ---", logfile)
                run_command(
                    f"ffplay -hide_banner -loglevel error "
                    f"-f v4l2 -input_format mjpeg -framerate {fps} "
                    f"-video_size {res} {dev}",
                    logfile
                )
                if ask_yes_no(f"Did you see video for {dev} at {res} MJPEG {fps}fps?"):
                    device_worked = True
                    log(f"{dev} at {res} MJPEG {fps}fps operator answered yes", logfile)

        # ----- YUYV test (commented out) -----
        # log("--- ffplay YUYV 640x480 10fps ---", logfile)
        # run_command(
        #     f"ffplay -hide_banner -loglevel error "
        #     f"-f v4l2 -input_format yuyv422 -framerate 10 -video_size 640x480 {dev}",
        #     logfile
        # )
        # if ask_yes_no(f"Did you see video for {dev} at 640x480 YUYV 10fps?"):
        #     device_worked = True
        #     log(f"video for {dev} at 640x480 YUYV 10fps operator answered yes", logfile)

        # ----- GStreamer JPEGDEC test (commented out) -----
        # log("--- GStreamer JPEGDEC test ---", logfile)
        # run_command(
        #     f"gst-launch-1.0 v4l2src device={dev} ! jpegdec ! fakesink",
        #     logfile
        # )
        # if ask_yes_no(f"Did you see video for {dev} (GStreamer JPEGDEC)?"):
        #     device_worked = True
        #     log(f"video for {dev} GStreamer JPEGDEC operator answered yes", logfile)

        # ----- Build report -----
        if device_worked:
            report.append(f"Device {dev} → ✅ WORKING")
        else:
            report.append(f"Device {dev} → ❌ NO VALID VIDEO")

        log("", logfile)

    # Final summary
    log("=== Troubleshoot Complete. Log saved to " + logfile, logfile)
    log("\n=== Report Summary ===", logfile)
    for line in report:
        log(line, logfile)

    print("\n".join(report))


if __name__ == "__main__":
    main()
