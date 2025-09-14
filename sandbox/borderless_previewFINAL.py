import gi
import sys
import os
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gtk, Gst, GstVideo, GdkX11, Gdk

# ------------- Configuration -------------
LOG_FILE = os.path.expanduser("~/borderless_preview.log")
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_X = 0
WINDOW_Y = 50
# -----------------------------------------

def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[{timestamp}] {message}"
    with open(LOG_FILE, 'a') as f:
        f.write(full_message + "\n")
        f.flush()
    print(full_message, flush=True)

# ------------- Argument Check -------------
if len(sys.argv) != 2:
    log("❌ Usage: python borderless_preview.py <video_device_name> (e.g. video2)")
    log(f"📄 Log written to: {LOG_FILE}")
    time.sleep(0.1)
    sys.exit(1)

video_device_name = sys.argv[1]
video_device_path = f"/dev/{video_device_name}"

if not os.path.exists(video_device_path):
    log(f"❌ Error: Device {video_device_path} not found.")
    log(f"📄 Log written to: {LOG_FILE}")
    time.sleep(0.1)
    sys.exit(1)

log(f"✅ Starting preview for device: {video_device_path}")

# ------------- Main GTK Window -------------
Gst.init(None)
Gtk.init(None)

class BorderlessVideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__()

        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.move(WINDOW_X, WINDOW_Y)
        self.connect("key-press-event", self.on_key_press)

        self.drawing_area = Gtk.DrawingArea()
        self.add(self.drawing_area)
        self.show_all()

        pipeline_str = f"""
            v4l2src device={video_device_path} ! image/jpeg, width=1280, height=720, framerate=60/1 !
            jpegdec ! videoconvert ! video/x-raw,format=RGBA ! queue !
            compositor name=comp sink_0::xpos=0 sink_0::ypos=0 !
            videoconvert ! xvimagesink name=vsink sync=false
        """

        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            log(f"❌ Failed to create pipeline: {e}")
            log(f"📄 Log written to: {LOG_FILE}")
            time.sleep(0.1)
            sys.exit(1)

        self.vsink = self.pipeline.get_by_name("vsink")

        bus = self.pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)

        self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, message):
        if message.get_structure() and message.get_structure().get_name() == "prepare-window-handle":
            window = self.drawing_area.get_window()
            if window:
                message.src.set_window_handle(window.get_xid())

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            log("🛑 ESC key pressed. Exiting preview window.")
            self.pipeline.set_state(Gst.State.NULL)
            log(f"📄 Log written to: {LOG_FILE}")
            Gtk.main_quit()

# ------------- Launch Application -------------
try:
    win = BorderlessVideoWindow()
    Gtk.main()
except Exception as ex:
    log(f"❌ Runtime error: {ex}")
    log(f"📄 Log written to: {LOG_FILE}")
    sys.exit(1)
