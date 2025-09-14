**2-in-1 Video Capture & Compositor Setup**

This guide explains how to set up, test, and troubleshoot a dual video-capture pipeline using Ubuntu Desktop (tested on VPro processor w/ 32 GB RAM & 16 GPU) or a Raspberry Pi 5 (8 GB RAM).

Original goal:
Combine two VGA video sources (from Derby Owners Club),  using HDMI upscalers and USB capture devices so as to process with GStreamer + Compositor feature + Python/GTK.

🖥️ Hardware Requirements

Qty: 2 — VGA male → VGA male (from Derby Owners Club main unit to HDMI upscalers)

Qty: 2 — 60 Hz USB-A video capture cards

Qty: 2 — VGA → HDMI upscalers (1920×1080 or 1280×720 supported)

🔌 Setup

Connect capture devices
Plug in both USB-A capture cards.

Discover devices

ls -al /dev/video*


List devices and capabilities

v4l2-ctl --list-devices


Example:

USB3.0 Capture: USB3.0 Capture (usb-0000:00:14.0-1):
    /dev/video4
    /dev/video5
    /dev/media2


Inspect video formats

v4l2-ctl --device=/dev/video4 --list-formats-ext
v4l2-ctl --device=/dev/video5 --list-formats-ext


Look for MJPG 1920x1080 at 30 fps or 60 fps.

🎥 Basic GStreamer Tests

Show test color bars:

gst-launch-1.0 v4l2src device=/dev/video4 ! videoconvert ! autovideosink


Minimal stream test:

gst-launch-1.0 v4l2src device=/dev/video4 ! videoconvert ! autovideosink


Known 1080p configuration:

gst-launch-1.0 v4l2src device=/dev/video4 ! \
  image/jpeg,width=1920,height=1080,framerate=30/1 ! \
  jpegdec ! autovideosink sync=false


Known 720p configuration:

gst-launch-1.0 v4l2src device=/dev/video4 ! \
  image/jpeg,width=1280,height=720,framerate=30/1 ! \
  jpegdec ! autovideosink sync=false


⚠️ Important: Set your monitor resolution to 1920×1080 for the best match to captured streams.

🔧 Troubleshooting

If frames are black, confirm the source device is powered and connected.

Using an HDMI splitter is recommended for setup and debugging.

Utility script:

video_troubleshoot.sh


Iterates through all /dev/video* devices and logs whether they are active.

🐍 Python Virtual Environment Setup

Install system libraries

sudo apt update
sudo apt install -y \
  v4l-utils \
  python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-gtk3 gstreamer1.0-x gstreamer1.0-gl \
  gstreamer1.0-plugins-base-apps


Verify compositor & sinks

gst-inspect-1.0 compositor | head
gst-inspect-1.0 gtksink   | head
gst-inspect-1.0 xvimagesink | head   # optional


Create a venv with system packages

python3 -m venv --system-site-packages gstenv
source gstenv/bin/activate


Do not pip install PyGObject or gstreamer wheels. Use system-provided gi.

Upgrade pip and pure-Python deps

pip install --upgrade pip wheel setuptools


Verify imports

python -c 'import gi; gi.require_version("Gst","1.0"); gi.require_version("Gtk","3.0"); from gi.repository import Gst, Gtk; print("GI OK")'


Run the compositor script

python Derby2in1.py video2 video4


Debug if blank

GST_DEBUG=2 python Derby2in1.py video2 video4


If still blank, test glimagesink instead of gtksink.

Extra checks

Confirm X11 vs Wayland:

echo "$XDG_SESSION_TYPE"


Ensure user is in video group:

groups | grep -w video || sudo usermod -aG video "$USER"

✅ Validate GStreamer Compositor

Minimal working test (two sources @ 640×480):

gst-launch-1.0 \
  compositor name=comp sink_0::xpos=0 sink_1::xpos=640 ! autovideosink \
  v4l2src device=/dev/video0 ! video/x-raw,width=640,height=480 ! queue ! comp. \
  v4l2src device=/dev/video2 ! video/x-raw,width=640,height=480 ! queue ! comp.


Would you like me to also add diagrams (e.g., a simple block diagram showing two VGA → HDMI → USB capture → GStreamer → compositor → sink) to the README? That could make the setup more beginner-friendly.


