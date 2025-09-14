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

        # choose sink
        if Gst.ElementFactory.find("gtksink"):
            self.sink_kind = "gtksink"
            sink_desc = "gtksink name=vsink"
        elif Gst.ElementFactory.find("glimagesink"):
            self.sink_kind = "glimagesink"
            sink_desc = "glimagesink name=vsink sync=false"
        else:
            self.sink_kind = "ximagesink"
            sink_desc = "ximagesink name=vsink sync=false"

        # compositor pipeline
        pipeline_str = f"""
        compositor name=comp latency=0 background=transparent ! \
            videoconvert ! {sink_desc} \
        v4l2src device={dev1} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
            videocrop name=crop1 left=0 right=0 top=0 bottom=0 ! \
            videoscale ! comp.sink_0 \
        v4l2src device={dev2} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
            videocrop name=crop2 left=0 right=0 top=0 bottom=0 ! \
            videoscale ! comp.sink_1
        """

        self.pipeline = Gst.parse_launch(pipeline_str)
        self.comp = self.pipeline.get_by_name("comp")
        self.vsink = self.pipeline.get_by_name("vsink")

        # UI
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        if self.sink_kind == "gtksink":
            video_widget = self.vsink.props.widget
            try:
                self.vsink.set_property("force-aspect-ratio", False)
            except Exception:
                pass
            vbox.pack_start(video_widget, True, True, 0)
        else:
            self.darea = Gtk.DrawingArea()
            vbox.pack_start(self.darea, True, True, 0)
            self.darea.connect("realize", self._on_realize)
            bus = self.pipeline.get_bus()
            bus.enable_sync_message_emission()
            bus.connect("sync-message::element", self._on_sync_msg)

        self.show_all()
        self.pipeline.set_state(Gst.State.PLAYING)
        self._apply_layout(*self.get_size())

    def _apply_layout(self, win_w: int, win_h: int):
        pads = self.comp.sinkpads
        if len(pads) < 2:
            return
        self.pad1, self.pad2 = pads[0], pads[1]
        w0 = win_w // 2
        w1 = win_w - w0
        h = win_h
        self.pad1.set_property("xpos", 0)
        self.pad1.set_property("ypos", 0)
        self.pad1.set_property("width", w0)
        self.pad1.set_property("height", h)

        self.pad2.set_property("xpos", w0)
        self.pad2.set_property("ypos", 0)
        self.pad2.set_property("width", w1)
        self.pad2.set_property("height", h)

    def on_resize(self, widget, event):
        alloc = widget.get_allocation()
        self._apply_layout(alloc.width, alloc.height)
        return False

    def _on_realize(self, widget):
        win = widget.get_window()
        if win and hasattr(self.vsink, "set_window_handle"):
            self.vsink.set_window_handle(win.get_xid())
        try:
            self.vsink.set_property("force-aspect-ratio", False)
        except Exception:
            pass

    def _on_sync_msg(self, _bus, msg):
        s = msg.get_structure()
        if s and s.get_name() == "prepare-window-handle" and hasattr(self, "darea"):
            win = self.darea.get_window()
            if win:
                try:
                    msg.src.set_window_handle(win.get_xid())
                except Exception:
                    pass

    def on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.quit()

    def quit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 borderless_dual_preview.py <video_device1> <video_device2>")
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
