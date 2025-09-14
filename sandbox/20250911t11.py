import gi
import sys
import os
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gtk, Gst, GdkX11, Gdk

# ------------- Configuration -------------
LOG_FILE = os.path.expanduser("~/borderless_preview.log")
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_X = 0
WINDOW_Y = 50
# -----------------------------------------

def log(message):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    with open(LOG_FILE, 'a') as f:
        f.write(msg + "\n")
        f.flush()
    print(msg, flush=True)

# ------------- Args -------------
if len(sys.argv) != 3:
    log("❌ Usage: python t5.py <video_device1> <video_device2>   (e.g. video0 video2)")
    sys.exit(1)

video_device1 = f"/dev/{sys.argv[1]}"
video_device2 = f"/dev/{sys.argv[2]}"
for p in (video_device1, video_device2):
    if not os.path.exists(p):
        log(f"❌ Error: Device {p} not found.")
        sys.exit(1)

log(f"✅ Starting preview for devices: {video_device1}, {video_device2}")

# ------------- GTK / GStreamer -------------
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

        # Container so we can pack either a DrawingArea or a gtksink widget
        self.box = Gtk.Box()
        self.add(self.box)
        self.show_all()

        # Pick best sink available: gtksink → glimagesink → ximagesink
        self.sink_kind = None
        for candidate in ("gtksink", "glimagesink", "ximagesink"):
            if Gst.ElementFactory.find(candidate):
                self.sink_kind = candidate
                break
        if not self.sink_kind:
            log("❌ No suitable video sink found (need gtksink/glimagesink/ximagesink).")
            sys.exit(1)

        if self.sink_kind == "gtksink":
            sink_desc = "gtksink name=vsink"
        elif self.sink_kind == "glimagesink":
            sink_desc = "glimagesink name=vsink sync=false"
        else:
            sink_desc = "ximagesink name=vsink sync=false"

        # --- pipeline string (no leading spaces inside triple quotes) ---
        pipeline_str = f"""
                                compositor name=comp latency=0 sink_1::xpos=640 sink_1::ypos=0 background=black ! \
                                    videoconvert ! {sink_desc} \
                                v4l2src device={video_device1} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! videoscale ! \
                                    video/x-raw,width=640,height=720 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! comp. \
                                v4l2src device={video_device2} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! videoscale ! \
                                    video/x-raw,width=640,height=720 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! comp.
                                """

        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            log(f"❌ Failed to create pipeline: {e}")
            sys.exit(1)

        self.vsink = self.pipeline.get_by_name("vsink")

        if self.sink_kind == "gtksink":
            try:
                sink_widget = self.vsink.get_property("widget")
            except Exception:
                sink_widget = None
            if sink_widget:
                for child in self.box.get_children():
                    self.box.remove(child)
                self.box.pack_start(sink_widget, True, True, 0)
                self.show_all()
                try:
                    self.vsink.set_property("force-aspect-ratio", False)
                except Exception:
                    pass
                self.pipeline.set_state(Gst.State.PLAYING)
            else:
                log("❌ gtksink present but no widget property; falling back to handle embedding.")
                self._embed_with_handle()
        else:
            self._embed_with_handle()

    def _embed_with_handle(self):
        self.drawing_area = Gtk.DrawingArea()
        for child in self.box.get_children():
            self.box.remove(child)
        self.box.pack_start(self.drawing_area, True, True, 0)
        self.show_all()

        try:
            self.vsink.set_property("force-aspect-ratio", False)
        except Exception:
            pass

        self.pipeline.set_state(Gst.State.READY)
        self.drawing_area.connect("realize", self.on_realize)

        bus = self.pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)

    def on_realize(self, widget):
        window = widget.get_window()
        if window and self.vsink:
            xid = window.get_xid()
            try:
                self.vsink.set_window_handle(xid)
            except Exception:
                pass
            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, message):
        s = message.get_structure()
        if not s:
            return
        if s.get_name() == "prepare-window-handle":
            if hasattr(self, "drawing_area"):
                window = self.drawing_area.get_window()
                if window:
                    try:
                        message.src.set_window_handle(window.get_xid())
                    except Exception:
                        pass

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            log("🛑 ESC key pressed. Exiting preview window.")
            self.pipeline.set_state(Gst.State.NULL)
            Gtk.main_quit()

# ------------- Launch -------------
try:
    win = BorderlessVideoWindow()
    Gtk.main()
except Exception as ex:
    log(f"❌ Runtime error: {ex}")
    sys.exit(1)


