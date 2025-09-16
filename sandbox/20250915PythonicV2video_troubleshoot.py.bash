import subprocess
import glob
import datetime
import sys

LOGFILE = f"video_test_{datetime.datetime.now().strftime('%Y%m%d-%H%M')}.log"

def log(msg):
    print(msg)
    with open(LOGFILE, "a") as f:
        f.write(msg + "\n")

def run_command(cmd):
    try:
        subprocess.run(cmd, shell=True, timeout=5, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        return False
    return True

def ask_user(prompt):
    ans = input(f"{prompt} (y/n): ").strip().lower()
    return ans == "y"

def test_ffplay_mjpeg(dev, res, fps):
    log(f"--- ffplay MJPEG {res} {fps}fps ---")
    cmd = f"ffplay -hide_banner -loglevel error -f v4l2 -input_format mjpeg -framerate {fps} -video_size {res} {dev}"
    run_command(cmd)
    return ask_user(f"Did you see video for {dev} at {res} MJPEG {fps}fps?")

def main():
    devices = glob.glob("/dev/video*")
    if not devices:
        log("No /dev/video* devices found.")
        sys.exit(1)

    report = []
    for dev in devices:
        log(f"===== Device: {dev} =====")
        worked = False
        for res in ["1920x1080", "1280x720", "640x480"]:
            if test_ffplay_mjpeg(dev, res, 30):
                worked = True
        report.append(f"{dev} → {'✅ WORKING' if worked else '❌ NO VALID VIDEO'}")

    log("=== Troubleshoot Complete ===")
    log("\n".join(report))
    print("\n".join(report))

if __name__ == "__main__":
    main()
