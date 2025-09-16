<img width="1591" height="695" alt="image" src="https://github.com/user-attachments/assets/464f0e5c-2b2f-4d76-8e5e-ac415159ed60" />





**2-in-1 Video Capture & Compositor Setup**

This guide explains how to set up, test, and troubleshoot a dual video-capture pipeline using Ubuntu Desktop (tested on VPro processor w/ 32 GB RAM & 16 GPU) or a Raspberry Pi 5 (8 GB RAM).

Original goal:
Combine two VGA video sources (from Derby Owners Club),  using HDMI upscalers and USB capture devices so as to process with GStreamer + Compositor feature + Python/GTK.

🖥️ Hardware Requirements
Video game with two VGA outputs.

Qty: 2 — VGA male → VGA male (from Derby Owners Club main unit to HDMI upscalers)

Qty: 2 — 1920x1080 and 1280x720 60 Hz USB-A video capture cards

Qty: 2 — VGA → HDMI upscalers (1920×1080 or 1280×720 supported)

🔌 Setup

Connect capture devices
Plug in both USB-A capture cards.

Execute discovery script from the directory you are in:
python3 DiscoverWorkingVideo.py
- make note of the video sources appearing and answer the questions correctly.
- take note of video# devices because you will need them when you execute the main script. 


🐍 Python Virtual Environment Setup
Required to run in ubuntu or rpi.

Before continuing you will need to have python referenced by python3.

In a BASH shell:
Create a venv with system packages. 

python3 -m venv --system-site-packages gstenv

source gstenv/bin/activate
- Look for a prompt to the left with  
(gstenv) 

Upgrade pip and pure-Python deps:
pip install --upgrade pip wheel setuptools


sudo apt update
- may take some time.

# Install gstreamer
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


Verify imports

python -c 'import gi; gi.require_version("Gst","1.0"); gi.require_version("Gtk","3.0"); from gi.repository import Gst, Gtk; print("GI OK")'


Run the compositor script with the video sources you gained when you ran DiscoverWorkingVideo.py:
python3 SEGADOC2in1Video.py video# video#


<img width="1761" height="1006" alt="image" src="https://github.com/user-attachments/assets/7393e798-9965-48ac-bfbc-edee85551c37" />



🔧 Troubleshooting


If frames are black, confirm the source device is powered and connected.

Using an HDMI splitter is recommended for setup and debugging.

Use the Utility script to search and display all formats of video input:
 DiscoverWorkingVideo.py
 The script helps you see which video devices are working.

 


