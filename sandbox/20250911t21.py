import subprocess

# =======================
# CONFIG SECTION
# =======================
# Crop settings
CROP_VIDEO2 = {"left": 30, "right": 39, "top": 0, "bottom": 0}
CROP_VIDEO4 = {"left": 30, "right": 39, "top": 0, "bottom": 0}

# Output resolution
WIDTH = 1280
HEIGHT = 720

# Gap/overlap setting
# Positive = gap, Negative = overlap
OVERLAP = -10  

# Video sink (use autovideosink if glimagesink fails)
SINK = "autovideosink"

# =======================
# PIPELINE BUILDER
# =======================
def build_pipeline_single(device, crop, width, height, sink):
    return (
        f"gst-launch-1.0 -v "
        f"v4l2src device={device} ! image/jpeg,framerate=60/1 ! jpegdec ! "
        f"videocrop left={crop['left']} right={crop['right']} "
        f"top={crop['top']} bottom={crop['bottom']} ! "
        f"videoscale ! video/x-raw,width={width},height={height},par=1/1 ! "
        f"videoconvert ! {sink}"
    )

def build_pipeline_compositor(crop2, crop4, width, height, overlap, sink):
    xpos2 = 0
    xpos4 = width + overlap  # offset applied here

    return (
        f"gst-launch-1.0 -v "
        f"compositor name=comp background=transparent "
        f"sink_0::xpos={xpos2} sink_1::xpos={xpos4} ! "
        f"video/x-raw,width={width*2},height={height} ! videoconvert ! {sink} "
        f"v4l2src device=/dev/video2 ! image/jpeg,framerate=60/1 ! jpegdec ! "
        f"videocrop left={crop2['left']} right={crop2['right']} "
        f"top={crop2['top']} bottom={crop2['bottom']} ! "
        f"videoscale ! video/x-raw,width={width},height={height},par=1/1 ! "
        f"videoconvert ! queue ! comp.sink_0 "
        f"v4l2src device=/dev/video4 ! image/jpeg,framerate=60/1 ! jpegdec ! "
        f"videocrop left={crop4['left']} right={crop4['right']} "
        f"top={crop4['top']} bottom={crop4['bottom']} ! "
        f"videoscale ! video/x-raw,width={width},height={height},par=1/1 ! "
        f"videoconvert ! queue ! comp.sink_1"
    )

def run_pipeline(pipeline):
    print(f"Running pipeline:\n{pipeline}\n")
    subprocess.run(pipeline, shell=True)

if __name__ == "__main__":
    print("Choose mode:")
    print("1. Video2 only")
    print("2. Video4 only")
    print("3. Dual feed compositor")
    choice = input("Enter 1/2/3: ").strip()

    if choice == "1":
        run_pipeline(build_pipeline_single("/dev/video2", CROP_VIDEO2, WIDTH, HEIGHT, SINK))
    elif choice == "2":
        run_pipeline(build_pipeline_single("/dev/video4", CROP_VIDEO4, WIDTH, HEIGHT, SINK))
    elif choice == "3":
        run_pipeline(build_pipeline_compositor(CROP_VIDEO2, CROP_VIDEO4, WIDTH, HEIGHT, OVERLAP, SINK))
    else:
        print("Invalid choice.")
