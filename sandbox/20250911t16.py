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

#        self.move(WINDOW_X, WINDOW_Y)
        self.set_resizable(True)

#         self.connect("key-press-event", self.on_key_press)
        self.connect("configure-event", self.on_resize)

        # Container for video + sliders
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.vbox)
        self.show_all()

        # Choose sink
        self.sink_kind = None
        for candidate in ("gtksink", "glimagesink", "ximagesink"):
            if Gst.ElementFactory.find(candidate):
                self.sink_kind = candidate
                break
        if not self.sink_kind:
            log("❌ No suitable video sink found (need gtksink/glimagesink/ximagesink).")
            sys.exit(1)

        sink_desc = (
            "gtksink name=vsink" if self.sink_kind == "gtksink"
            else "glimagesink name=vsink sync=false"
            if self.sink_kind == "glimagesink"
            else "ximagesink name=vsink sync=false"
        )

        # Pipeline
        pipeline_str = f"""
compositor name=comp latency=0 background=black ! \
    videoconvert ! {sink_desc} \
v4l2src device={video_device1} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! videoscale ! \
    video/x-raw,width=640,height=720 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! comp.sink_0 \
v4l2src device={video_device2} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! videoscale ! \
    video/x-raw,width=640,height=720 ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 leaky=downstream ! comp.sink_1
"""
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            log(f"❌ Failed to create pipeline: {e}")
            sys.exit(1)

        self.vsink = self.pipeline.get_by_name("vsink")
        self.compositor = self.pipeline.get_by_name("comp")

        # Sink embedding
        if self.sink_kind == "gtksink":
            try:
                sink_widget = self.vsink.get_property("widget")
            except Exception:
                sink_widget = None
            if sink_widget:
                self.vbox.pack_start(sink_widget, True, True, 0)
                self.show_all()
                self.pipeline.set_state(Gst.State.PLAYING)
            else:
                self._embed_with_handle()
        else:
            self._embed_with_handle()

        # --- Sliders for both pads ---
        sinkpads = self.compositor.sinkpads
        if len(sinkpads) >= 2:
            self.pad1 = sinkpads[0]  # first feed
            self.pad2 = sinkpads[1]  # second feed

            # Controls for first feed
            self.add_slider("Feed1 X", 0, WINDOW_WIDTH, self.pad1.get_property("xpos"), self.on_x1_changed)
            self.add_slider("Feed1 Y", 0, WINDOW_HEIGHT, self.pad1.get_property("ypos"), self.on_y1_changed)
            self.add_slider("Feed1 Width", 100, WINDOW_WIDTH, self.pad1.get_property("width"), self.on_w1_changed)
            self.add_slider("Feed1 Height", 100, WINDOW_HEIGHT, self.pad1.get_property("height"), self.on_h1_changed)
            self.add_slider("Feed1 Alpha", 0.0, 1.0, self.pad1.get_property("alpha"), self.on_a1_changed, step=0.01)

            # Controls for second feed
            self.add_slider("Feed2 X", 0, WINDOW_WIDTH, self.pad2.get_property("xpos"), self.on_x2_changed)
            self.add_slider("Feed2 Y", 0, WINDOW_HEIGHT, self.pad2.get_property("ypos"), self.on_y2_changed)
            self.add_slider("Feed2 Width", 100, WINDOW_WIDTH, self.pad2.get_property("width"), self.on_w2_changed)
            self.add_slider("Feed2 Height", 100, WINDOW_HEIGHT, self.pad2.get_property("height"), self.on_h2_changed)
            self.add_slider("Feed2 Alpha", 0.0, 1.0, self.pad2.get_property("alpha"), self.on_a2_changed, step=0.01)

    # Helper to add sliders
    def add_slider(self, label, min_val, max_val, init_val, callback, step=1):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label)
        adj = Gtk.Adjustment(init_val, min_val, max_val, step, step*10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(2 if isinstance(init_val, float) else 0)
        scale.connect("value-changed", callback)
        box.pack_start(lbl, False, False, 0)
        box.pack_start(scale, True, True, 0)
        self.vbox.pack_start(box, False, False, 0)
        self.show_all()

    # Feed1 controls
    def on_x1_changed(self, scale): self.pad1.set_property("xpos", int(scale.get_value()))
    def on_y1_changed(self, scale): self.pad1.set_property("ypos", int(scale.get_value()))
    def on_w1_changed(self, scale): self.pad1.set_property("width", int(scale.get_value()))
    def on_h1_changed(self, scale): self.pad1.set_property("height", int(scale.get_value()))
    def on_a1_changed(self, scale): self.pad1.set_property("alpha", float(scale.get_value()))

    # Feed2 controls
    def on_x2_changed(self, scale): self.pad2.set_property("xpos", int(scale.get_value()))
    def on_y2_changed(self, scale): self.pad2.set_property("ypos", int(scale.get_value()))
    def on_w2_changed(self, scale): self.pad2.set_property("width", int(scale.get_value()))
    def on_h2_changed(self, scale): self.pad2.set_property("height", int(scale.get_value()))
    def on_a2_changed(self, scale): self.pad2.set_property("alpha", float(scale.get_value()))

    # Embed with DrawingArea for non-gtksink
    def _embed_with_handle(self):
        self.drawing_area = Gtk.DrawingArea()
        self.vbox.pack_start(self.drawing_area, True, True, 0)
        self.show_all()
        self.pipeline.set_state(Gst.State.READY)
        self.drawing_area.connect("realize", self.on_realize)
        bus = self.pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)

    def on_realize(self, widget):
        window = widget.get_window()
        if window and self.vsink:
            xid = window.get_xid()
            try: self.vsink.set_window_handle(xid)
            except Exception: pass
            self.pipeline.set_state(Gst.State.PAUSED)
            self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, message):
        s = message.get_structure()
        if s and s.get_name() == "prepare-window-handle":
            if hasattr(self, "drawing_area"):
                window = self.drawing_area.get_window()
                if window:
                    try: message.src.set_window_handle(window.get_xid())
                    except Exception: pass

    def on_resize(self, widget, event):
        alloc = widget.get_allocation()
        new_w, new_h = alloc.width, alloc.height
        # Update both feeds to new window size
        self.pad1.set_property("width", new_w)
        self.pad1.set_property("height", new_h)
        self.pad2.set_property("width", new_w)
        self.pad2.set_property("height", new_h)



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


