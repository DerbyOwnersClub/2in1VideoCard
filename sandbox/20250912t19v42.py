import gi
import sys
import os
import time

gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gtk, Gst, GdkX11, Gdk

# -------- Config --------
LOG_FILE = os.path.expanduser("~/borderless_preview.log")
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
WINDOW_X = 0
WINDOW_Y = 0
# ------------------------


def log(message):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    with open(LOG_FILE, 'a') as f:
        f.write(msg + "\n")
        f.flush()
    print(msg, flush=True)

# ---- Args ----
if len(sys.argv) != 3:
    log("❌ Usage: python script.py <video_device1> <video_device2> (e.g. video0 video2)")
    sys.exit(1)

video_device1 = f"/dev/{sys.argv[1]}"
video_device2 = f"/dev/{sys.argv[2]}"
for p in (video_device1, video_device2):
    if not os.path.exists(p):
        log(f"❌ Error: Device {p} not found.")
        sys.exit(1)

log(f"✅ Starting preview for devices: {video_device1}, {video_device2}")

# ---- Init ----
Gst.init(None)
Gtk.init(None)

class BorderlessVideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(True)
        self.move(WINDOW_X, WINDOW_Y)
        self.connect("key-press-event", self.on_key_press)
        self.connect("configure-event", self.on_resize)
        self.base_w, self.base_h = WINDOW_WIDTH, WINDOW_HEIGHT

        # Layout
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.vbox)
        self.show_all()

        # Choose sink
        self.sink_kind = None
        for cand in ("gtksink", "glimagesink", "ximagesink"):
            if Gst.ElementFactory.find(cand):
                self.sink_kind = cand
                break
        if not self.sink_kind:
            log("❌ No suitable video sink found.")
            sys.exit(1)

        sink_desc = (
            "gtksink name=vsink" if self.sink_kind == "gtksink"
            else "glimagesink name=vsink sync=false"
            if self.sink_kind == "glimagesink"
            else "ximagesink name=vsink sync=false"
        )

        half_w = WINDOW_WIDTH // 2

        # Pipeline
        pipeline_str = f"""
compositor name=comp latency=0 background=transparent ! \
    videoconvert ! {sink_desc} \
v4l2src device={video_device1} io-mode=2 do-timestamp=true ! \
    image/jpeg,framerate=60/1 ! jpegdec ! \
    videocrop name=crop1 left=0 right=0 top=0 bottom=0 ! \
    videoscale ! video/x-raw,width={half_w},height={WINDOW_HEIGHT} ! comp.sink_0 \
v4l2src device={video_device2} io-mode=2 do-timestamp=true ! \
    image/jpeg,framerate=30/1 ! jpegdec ! \
    videocrop name=crop2 left=40 right=0 top=0 bottom=0 ! \
    videoscale ! video/x-raw,width={half_w},height={WINDOW_HEIGHT} ! comp.sink_1
"""
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            log(f"❌ Failed to create pipeline: {e}")
            sys.exit(1)

        self.vsink = self.pipeline.get_by_name("vsink")
        self.compositor = self.pipeline.get_by_name("comp")
        self.crop1 = self.pipeline.get_by_name("crop1")
        self.crop2 = self.pipeline.get_by_name("crop2")

        # Embed sink
        if self.sink_kind == "gtksink":
            try:
                sink_widget = self.vsink.get_property("widget")
            except Exception:
                sink_widget = None
            if sink_widget:
                self.vbox.pack_start(sink_widget, True, True, 0)
                self.show_all()
                try:
                    self.vsink.set_property("force-aspect-ratio", False)
                except Exception:
                    pass
                self.pipeline.set_state(Gst.State.PLAYING)
            else:
                self._embed_with_handle()
        else:
            self._embed_with_handle()

        # Pads
        sinkpads = self.compositor.sinkpads
        if len(sinkpads) >= 2:
            self.pad1, self.pad2 = sinkpads[0], sinkpads[1]
            self._apply_layout(self.base_w, self.base_h)

            # Sliders
            self.add_slider("Feed1 Alpha", 0.0, 1.0, 1.0, self.on_a1, step=0.01)
            self.add_slider("Feed1 Zorder", 0, 10, 0, self.on_z1)
            self.add_slider("Feed1 Crop Left", 0, 200, 0, self.on_c1_left)

            self.add_slider("Feed2 Alpha", 0.0, 1.0, 1.0, self.on_a2, step=0.01)
            self.add_slider("Feed2 Zorder", 0, 10, 1, self.on_z2)
            self.add_slider("Feed2 Crop Left", 0, 200, 40, self.on_c2_left)

    # ---- Helpers ----
    def add_slider(self, label, minv, maxv, initv, cb, step=1):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label); lbl.set_xalign(0.0)
        adj = Gtk.Adjustment(initv, minv, maxv, step, step*10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(2 if isinstance(initv, float) else 0)
        scale.set_value(initv)
        scale.connect("value-changed", cb)
        row.pack_start(lbl, False, False, 6)
        row.pack_start(scale, True, True, 6)
        self.vbox.pack_start(row, False, False, 2)
        self.show_all()

    def _apply_layout(self, win_w, win_h):
        half_w = win_w // 2
        self.pad1.set_property("xpos", 0)
        self.pad1.set_property("ypos", 0)
        self.pad1.set_property("width", half_w)
        self.pad1.set_property("height", win_h)

        self.pad2.set_property("xpos", half_w)
        self.pad2.set_property("ypos", 0)
        self.pad2.set_property("width", win_w - half_w)
        self.pad2.set_property("height", win_h)

    def on_resize(self, widget, event):
        alloc = widget.get_allocation()
        self.base_w, self.base_h = alloc.width, alloc.height
        self._apply_layout(self.base_w, self.base_h)

    # ---- Callbacks ----
    def on_a1(self, s): self.pad1.set_property("alpha", float(s.get_value()))
    def on_z1(self, s): self.pad1.set_property("zorder", int(s.get_value()))
    def on_c1_left(self, s): self.crop1.set_property("left", int(s.get_value()))

    def on_a2(self, s): self.pad2.set_property("alpha", float(s.get_value()))
    def on_z2(self, s): self.pad2.set_property("zorder", int(s.get_value()))
    def on_c2_left(self, s): self.crop2.set_property("left", int(s.get_value()))

    # ---- Embedding ----
    def _embed_with_handle(self):
        self.darea = Gtk.DrawingArea()
        self.vbox.pack_start(self.darea, True, True, 0)
        self.show_all()
        try: self.vsink.set_property("force-aspect-ratio", False)
        except Exception: pass
        self.pipeline.set_state(Gst.State.READY)
        self.darea.connect("realize", self.on_realize)
        bus = self.pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)

    def on_realize(self, widget):
        win = widget.get_window()
        if win and self.vsink:
            try: self.vsink.set_window_handle(win.get_xid())
            except Exception: pass
            self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, msg):
        st = msg.get_structure()
        if st and st.get_name() == "prepare-window-handle":
            if hasattr(self, "darea"):
                win = self.darea.get_window()
                if win:
                    try: msg.src.set_window_handle(win.get_xid())
                    except Exception: pass

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            log("🛑 ESC pressed. Exiting.")
            self.pipeline.set_state(Gst.State.NULL)
            Gtk.main_quit()

# ---- Launch ----
try:
    win = BorderlessVideoWindow()
    Gtk.main()
except Exception as ex:
    log(f"❌ Runtime error: {ex}")
    sys.exit(1)
