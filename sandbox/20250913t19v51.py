
#
# Date: 20250913
#
#
# Purpose:


# Revision History
# 
#
# Date          | Description       | Author
#-----------------------------------------------------
# 20250913  | Maker               | TFR
#
#
#
# Tested Crop Values
# ----------------------------------
# Resolution    | Feed | Value 
#---------------------------------------------
# 1920x1080    | 1R    | 53
# 1920x1080    | 2L    | 43
#
# 1920x1080    | 1R    | 53
# 1920x1080    | 2L    | 44
#
# 1920x1080    | 1R    | 53
# 1920x1080    | 2L    | 40
#
#

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
WINDOW_Y = 50
# ------------------------


def log(message):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {message}"
    with open(LOG_FILE, 'a') as f:
        f.write(msg + "\n"); f.flush()
    print(msg, flush=True)

# Args
if len(sys.argv) != 3:
    log("❌ Usage: python t.py <video_device1> <video_device2>   (e.g. video0 video2)")
    sys.exit(1)

video_device1 = f"/dev/{sys.argv[1]}"
video_device2 = f"/dev/{sys.argv[2]}"
for p in (video_device1, video_device2):
    if not os.path.exists(p):
        log(f"❌ Error: Device {p} not found."); sys.exit(1)

log(f"✅ Starting preview for devices: {video_device1}, {video_device2}")

# GTK / GStreamer init
Gst.init(None)
Gtk.init(None)

class BorderlessVideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(True)         # allow maximize
        self.move(WINDOW_X, WINDOW_Y)
        self.connect("key-press-event", self.on_key_press)
        self.connect("configure-event", self.on_resize)
        self.base_w, self.base_h = WINDOW_WIDTH, WINDOW_HEIGHT

        # Layout: video on top, sliders below
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(self.vbox)
        self.show_all()

        # Choose sink: gtksink > glimagesink > ximagesink
        self.sink_kind = None
        for cand in ("gtksink", "glimagesink", "ximagesink"):
            if Gst.ElementFactory.find(cand):
                self.sink_kind = cand; break
        if not self.sink_kind:
            log("❌ No suitable video sink found (need gtksink/glimagesink/ximagesink).")
            sys.exit(1)

        sink_desc = (
            "gtksink name=vsink" if self.sink_kind == "gtksink"
            else "glimagesink name=vsink sync=false"
            if self.sink_kind == "glimagesink"
            else "ximagesink name=vsink sync=false"
        )

        # >>> Merged change: scale each feed to half width and use transparent background
        half_w = WINDOW_WIDTH // 2


        # Pipeline with videocrop on each feed, no hardcoded scaling to 1920x1080

        pipeline_str = f"""
        compositor name=comp latency=0 background=transparent ! \
            videoconvert ! {sink_desc} \
        v4l2src device={video_device1} io-mode=2 do-timestamp=true ! \
            image/jpeg,framerate=60/1 ! jpegdec ! \
            videoscale ! video/x-raw,pixel-aspect-ratio=1/1 ! \
            videocrop name=crop1 top=0 bottom=0 left=0 right=53 ! \
            videoconvert ! queue ! comp.sink_0 \
        v4l2src device={video_device2} io-mode=2 do-timestamp=true ! \
            image/jpeg,framerate=60/1 ! jpegdec ! \
            videoscale ! video/x-raw,pixel-aspect-ratio=1/1 ! \
            videocrop name=crop2 top=0 bottom=0 left=43 right=0 ! \
            videoconvert ! queue ! comp.sink_1
        """


        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            log(f"❌ Failed to create pipeline: {e}"); sys.exit(1)

        self.vsink = self.pipeline.get_by_name("vsink")
        self.compositor = self.pipeline.get_by_name("comp")
        self.crop1 = self.pipeline.get_by_name("crop1")
        self.crop2 = self.pipeline.get_by_name("crop2")

        # Embed video
        if self.sink_kind == "gtksink":
            try:
                sink_widget = self.vsink.get_property("widget")
            except Exception:
                sink_widget = None
            if sink_widget:
                self.vbox.pack_start(sink_widget, True, True, 0)
                self.show_all()
                try: self.vsink.set_property("force-aspect-ratio", False)
                except Exception: pass
                self.pipeline.set_state(Gst.State.PLAYING)
            else:
                self._embed_with_handle()
        else:
            self._embed_with_handle()

        # ---- Controls ----
        sinkpads = self.compositor.sinkpads
        if len(sinkpads) >= 2:
            self.pad1 = sinkpads[0]
            self.pad2 = sinkpads[1]

# Positioning of windows

            w0 = self.base_w // 2
            w1 = self.base_w - w0
            h  = self.base_h

            # >>> Merged change: feed1 left half, feed2 right half

            # feed1 on the left
            self.pad1.set_property("xpos", 0)
            self.pad1.set_property("ypos", 0)
            self.pad1.set_property("width", self.base_w // 2)
            self.pad1.set_property("height", self.base_h)

            # feed2 on the right
            self.pad2.set_property("xpos", self.base_w // 2)
            self.pad2.set_property("ypos", 0)
            self.pad2.set_property("width", self.base_w // 2)
            self.pad2.set_property("height", self.base_h)

###
#            # Start both feeds full-window
            self.pad1.set_property("xpos", 0); self.pad1.set_property("ypos", 0)
            self.pad2.set_property("xpos", 0); self.pad2.set_property("ypos", 0)
#
#            self.pad1.set_property("width", self.base_w); self.pad1.set_property("height", self.base_h)
 #           self.pad2.set_property("width", self.base_w); self.pad2.set_property("height", self.base_h)
####

#!@
        w0 = self.base_w // 2
        w1 = self.base_w - w0
        h  = self.base_h

#        # feed1 on the left
        self.pad1.set_property("xpos", 0)
        self.pad1.set_property("ypos", 0)
        self.pad1.set_property("width", w0)
        self.pad1.set_property("height", h)
#
#        # feed2 on the right
        self.pad2.set_property("xpos", w0)
        self.pad2.set_property("ypos", 0)
        self.pad2.set_property("width", w1)
        self.pad2.set_property("height", h)
#!@

            # Feed1 sliders
        self.add_slider("Feed1 X", 0, self.base_w, 0, self.on_x1)
        self.add_slider("Feed1 Y", 0, self.base_h, 0, self.on_y1)
        self.add_slider("Feed1 Zoom", 0.5, 2.0, 1.0, self.on_zoom1, step=0.01)
#            self.add_slider("Feed1 Alpha", 0.0, 1.0, 1.0, self.on_a1, step=0.01)
#           self.add_slider("Feed1 Zorder", 0, 10, 0, self.on_z1, step=1)
        self.add_slider("Feed1 Crop Left", 0, 300, 0, self.on_c1_left)
        self.add_slider("Feed1 Crop Right", 0, 300, 0, self.on_c1_right)
        self.add_slider("Feed1 Crop Top", 0, 300, 0, self.on_c1_top)
        self.add_slider("Feed1 Crop Bottom", 0, 300, 0, self.on_c1_bottom)

            # Feed2 sliders
        self.add_slider("Feed2 X", 0, self.base_w, w0, self.on_x2)
        self.add_slider("Feed2 Y", 0, self.base_h, 0, self.on_y2)
        self.add_slider("Feed2 Zoom", 0.5, 2.0, 1.0, self.on_zoom2, step=0.01)
#            self.add_slider("Feed2 Alpha", 0.0, 1.0, 1.0, self.on_a2, step=0.01)
#           self.add_slider("Feed2 Zorder", 0, 10, 1, self.on_z2, step=1)
        self.add_slider("Feed2 Crop Left", 0, 300, 0, self.on_c2_left)
        self.add_slider("Feed2 Crop Right", 0, 300, 0, self.on_c2_right)
        self.add_slider("Feed2 Crop Top", 0, 300, 0, self.on_c2_top)
        self.add_slider("Feed2 Crop Bottom", 0, 300, 0, self.on_c2_bottom)

    # ---- UI helper ----
    def add_slider(self, label, minv, maxv, initv, cb, step=1):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label); lbl.set_xalign(0.0)
        adj = Gtk.Adjustment(initv, minv, maxv, step, step*10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(2 if isinstance(initv, float) else 0)
        scale.connect("value-changed", cb)
        row.pack_start(lbl, False, False, 6)
        row.pack_start(scale, True, True, 6)
        self.vbox.pack_start(row, False, False, 2)
        self.show_all()

    # ---- Feed1 callbacks ----
    def on_x1(self, s): self.pad1.set_property("xpos", int(s.get_value()))
    def on_y1(self, s): self.pad1.set_property("ypos", int(s.get_value()))
    def on_zoom1(self, s):
       z = float(s.get_value())
       self.pad1.set_property("width", int(self.base_w * z))
       self.pad1.set_property("height", int(self.base_h * z))
    def on_a1(self, s): self.pad1.set_property("alpha", float(s.get_value()))
    def on_z1(self, s): self.pad1.set_property("zorder", int(s.get_value()))
    
    def on_c1_left(self, s):
        val = int(s.get_value())
        self.crop1.set_property("left", val)
        log(f"Feed1 Crop Left = {val}")

    def on_c1_right(self, s):
        val = int(s.get_value())
        self.crop1.set_property("right", val)
        log(f"Feed1 Crop Right = {val}")

    def on_c1_top(self, s):
        val = int(s.get_value())
        self.crop1.set_property("top", val)
        log(f"Feed1 Crop Top = {val}")

    def on_c1_bottom(self, s):
        val = int(s.get_value())
        self.crop1.set_property("bottom", val)
        log(f"Feed1 Crop Bottom = {val}")

    # ---- Feed2 callbacks ----
    def on_x2(self, s): self.pad2.set_property("xpos", int(s.get_value()))
    def on_y2(self, s): self.pad2.set_property("ypos", int(s.get_value()))
    def on_zoom2(self, s):
        z = float(s.get_value())
        self.pad2.set_property("width", int(self.base_w * z))
        self.pad2.set_property("height", int(self.base_h * z))
    def on_a2(self, s): self.pad2.set_property("alpha", float(s.get_value()))
    def on_z2(self, s): self.pad2.set_property("zorder", int(s.get_value()))


    def on_c2_left(self, s):
        val = int(s.get_value())
        self.crop2.set_property("left", val)
        log(f"Feed2 Crop Left = {val}")

    def on_c2_right(self, s):
        val = int(s.get_value())
        self.crop2.set_property("right", val)
        log(f"Feed2 Crop Right = {val}")

    def on_c2_top(self, s):
        val = int(s.get_value())
        self.crop2.set_property("top", val)
        log(f"Feed2 Crop Top = {val}")

    def on_c2_bottom(self, s):
        val = int(s.get_value())
        self.crop2.set_property("bottom", val)
        log(f"Feed2 Crop Bottom = {val}")

    # ---- Resize handling ----
    def on_resize(self, widget, event):
        alloc = widget.get_allocation()
        self.base_w, self.base_h = alloc.width, alloc.height
        if hasattr(self, "pad1") and hasattr(self, "pad2"):
            half_w = self.base_w // 2
            self.pad1.set_property("xpos", 0)
            self.pad1.set_property("ypos", 0)
            self.pad1.set_property("width", half_w)
            self.pad1.set_property("height", self.base_h)

            self.pad2.set_property("xpos", half_w)
            self.pad2.set_property("ypos", 0)
            self.pad2.set_property("width", self.base_w - half_w)
            self.pad2.set_property("height", self.base_h)

    # ---- Embedding for non-gtksink ----
    def _embed_with_handle(self):
        self.drawing_area = Gtk.DrawingArea()
        self.vbox.pack_start(self.drawing_area, True, True, 0)
        self.show_all()
        try: self.vsink.set_property("force-aspect-ratio", False)
        except Exception: pass

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
        st = message.get_structure()
        if st and st.get_name() == "prepare-window-handle":
            if hasattr(self, "drawing_area"):
                window = self.drawing_area.get_window()
                if window:
                    try: message.src.set_window_handle(window.get_xid())
                    except Exception: pass

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            log("🛑 ESC key pressed. Exiting preview window.")
            self.pipeline.set_state(Gst.State.NULL)
            Gtk.main_quit()

# Launch
try:
    win = BorderlessVideoWindow()
    Gtk.main()
except Exception as ex:
    log(f"❌ Runtime error: {ex}")
    sys.exit(1)
