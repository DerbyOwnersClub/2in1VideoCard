#!/usr/bin/env python3
import subprocess
import time
import os
import signal

def test_ffplay(device="/dev/video2", res="1280x720", fps=30, duration=5):
    cmd = [
        "ffplay", "-hide_banner", "-loglevel", "error",
        "-f", "v4l2",
        "-input_format", "mjpeg",
        "-framerate", str(fps),
        "-video_size", res,
        device
    ]

    # Start ffplay as subprocess in its own process group
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)

    try:
        # Let ffplay run for N seconds
        time.sleep(duration)
    finally:
        # Kill the whole process group so ffplay closes cleanly
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()

if __name__ == "__main__":
    print("Testing /dev/video2 at 1280x720 30fps for 5 seconds...")
    test_ffplay("/dev/video2", "1280x720", 30, 5)
    print("Test complete.")
