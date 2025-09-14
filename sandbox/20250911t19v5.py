import gi, sys, os
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst, Gtk, Gdk

Gst.init(None)

def devpath(arg: str) -> str:
    return arg if arg.startswith("/dev/") else f"/dev/{arg}"

class BorderlessVideoWindow(Gtk.Window):
    def __init__(self, dev1: str, dev2: str):
        
        
        super().__init__(title="Borderless Dual Preview")
        self.set_decorated(False)
        self.move(0, 0)
        self.fullscreen()
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", self.quit)
        self.connect("configure-event", self.on_resize)

        # pick a sink and its description string
        if Gst.ElementFactory.find("gtksink"):
            self.sink_kind = "gtksink"
            sink_desc = "gtksink name=vsink"
        elif Gst.ElementFactory.find("glimagesink"):
            self.sink_kind = "glimagesink"
            sink_desc = "glimagesink name=vsink sync=false"
        else:
            self.sink_kind = "ximagesink"
            sink_desc = "ximagesink name=vsink sync=false"

        # compositor with transparent background (no hard border color)
        pipeline_str = f"""
        compositor name=comp latency=0 background=transparent ! \
            videoconvert ! {sink_desc} \
        v4l2src device={video_device1} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
            videocrop name=crop1 left=0 right=0 top=0 bottom=0 ! \
            videoscale ! video/x-raw,width={WINDOW_WIDTH},height={WINDOW_HEIGHT} ! comp.sink_0 \
        v4l2src device={video_device2} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
            videocrop name=crop2 left=0 right=0 top=0 bottom=0 ! \
            videoscale ! video/x-raw,width={WINDOW_WIDTH},height={WINDOW_HEIGHT} ! comp.sink_1
        """

        self.pipeline = Gst.parse_launch(pipeline_str)
        self.comp = self.pipeline.get_by_name("comp")
        self.vsink = self.pipeline.get_by_name("vsink")

        # UI container
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # embed sink widget or provide a DrawingArea for gl/ximagesink
        if self.sink_kind == "gtksink":
            video_widget = self.vsink.props.widget
            # fill allocated area without letterbox
            try: self.vsink.set_property("force-aspect-ratio", False)
            except Exception: pass
            vbox.pack_start(video_widget, True, True, 0)
        else:
            self.darea = Gtk.DrawingArea()
            vbox.pack_start(self.darea, True, True, 0)
            self.darea.connect("realize", self._on_realize)
            # also pass handle via bus just in case
            bus = self.pipeline.get_bus()
            bus.enable_sync_message_emission()
            bus.connect("sync-message::element", self._on_sync_msg)

        self.show_all()

        # start and set an initial layout that avoids seams
        self.pipeline.set_state(Gst.State.PLAYING)
        self._apply_layout(*self.get_size())

    # ----- layout helpers -----
    def _apply_layout(self, win_w: int, win_h: int):
        """Split width exactly in two, give the right pad the remainder pixel, set pad sizes/positions."""
        if not self.comp or len(self.comp.sinkpads) < 2:
            return
        pad0, pad1 = self.comp.sinkpads[0], self.comp.sinkpads[1]

        w0 = win_w // 2
        w1 = win_w - w0   # ensures w0 + w1 == win_w (no 1px gap)
        h  = win_h

        pad0.set_property("xpos", 0)
        pad0.set_property("ypos", 0)
        pad0.set_property("width", w0)
        pad0.set_property("height", h)

        pad1.set_property("xpos", w0)   # butt up against pad0 exactly
        pad1.set_property("ypos", 0)
        pad1.set_property("width", w1)
        pad1.set_property("height", h)

        self.add_slider("Seam Adjust", -10, 10, 0, self.on_seam)
         
    # Callback:
    def on_seam(self, scale):
        val = int(scale.get_value())
        # shift feed2 slightly left/right
        self.pad2.set_property("xpos", val + self.base_w // 2)     

    def on_resize(self, widget, event):
        alloc = widget.get_allocation()
        self._apply_layout(alloc.width, alloc.height)
        return False

    # ----- embedding for non-gtksink sinks -----
    def _on_realize(self, widget):
        try:
            window = widget.get_window()
            if window and hasattr(self.vsink, "set_window_handle"):
                self.vsink.set_window_handle(window.get_xid())
            # fill widget without letterbox
            try: self.vsink.set_property("force-aspect-ratio", False)
            except Exception: pass
        except Exception:
            pass

    def _on_sync_msg(self, _bus, msg):
        s = msg.get_structure()
        if s and s.get_name() == "prepare-window-handle":
            if hasattr(self, "darea"):
                win = self.darea.get_window()
                if win:
                    try: msg.src.set_window_handle(win.get_xid())
                    except Exception: pass

    # ----- lifecycle -----
    def on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.quit()

    def quit(self, *args):
        try: self.pipeline.set_state(Gst.State.NULL)
        finally: Gtk.main_quit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 borderless_dual_preview.py <video_device1> <video_device2>  (e.g. video0 video2)")
        sys.exit(1)
    dev1 = devpath(sys.argv[1])
    dev2 = devpath(sys.argv[2])
    for d in (dev1, dev2):
        if not os.path.exists(d):
            print(f"Device not found: {d}")
            sys.exit(1)
    app = BorderlessVideoWindow(dev1, dev2)
    app.show_all()
    Gtk.main()
