import gi, sys, os
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst, Gtk, GObject, Gdk

# Init
GObject.threads_init()
Gst.init(None)

def devpath(name: str) -> str:
    return name if name.startswith("/dev/") else f"/dev/{name}"

class DualFeedApp(Gtk.Window):
    def __init__(self, dev1, dev2):
        super().__init__(title="Dual Feed (seam fix)")
        self.set_decorated(False)
        self.move(0, 0)
        self.fullscreen()
        self.connect("key-press-event", self.on_key)
        self.connect("destroy", self.quit)

        # choose sink: gtksink -> glimagesink
        sink_factory = "gtksink" if Gst.ElementFactory.find("gtksink") else "glimagesink"

        # Seam fixes:
        # - crop 1px from left of right feed (adjust 'left=' below)
        # - shift right feed xpos one pixel left (xpos=639)
        pipeline_str = f"""
compositor name=comp background=black ! videoconvert ! {sink_factory} name=sink
v4l2src device={dev1} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
    videoscale ! video/x-raw,width=640,height=720 ! \
    videocrop name=crop1 right=0 left=0 top=0 bottom=0 ! comp.sink_0
v4l2src device={dev2} io-mode=2 do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! \
    videoscale ! video/x-raw,width=640,height=720 ! \
    videocrop name=crop2 left=1 right=0 top=0 bottom=0 ! \
    comp.sink_1 sink_1::xpos=639
"""
        # NOTE: If you previously wanted a permanent 8px trim on the right feed,
        # set 'left=9' above (8 bezel + 1px seam overlap).

        self.pipeline = Gst.parse_launch(pipeline_str)

        sink = self.pipeline.get_by_name("sink")
        if sink_factory == "gtksink":
            video_widget = sink.props.widget
        else:
            # glimagesink will be embedded via realize; create a DrawingArea
            video_widget = Gtk.DrawingArea()
            video_widget.connect("realize", self._on_realize, sink)

        # layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.pack_start(video_widget, True, True, 0)
        self.add(vbox)

        # start
        self.pipeline.set_state(Gst.State.PLAYING)

    def _on_realize(self, widget, sink):
        # embed glimagesink into the DrawingArea if we fell back
        try:
            window = widget.get_window()
            if window is not None:
                xid = window.get_xid()
                if hasattr(sink, "set_window_handle"):
                    sink.set_window_handle(xid)
        except Exception:
            pass

    def on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.quit()

    def quit(self, *args):
        try:
            self.pipeline.set_state(Gst.State.NULL)
        finally:
            Gtk.main_quit()

if __name__ == "__main__":
    # parse devices; defaults if not provided
    dev1 = devpath(sys.argv[1]) if len(sys.argv) > 1 else "/dev/video0"
    dev2 = devpath(sys.argv[2]) if len(sys.argv) > 2 else "/dev/video2"
    # sanity check
    for d in (dev1, dev2):
        if not os.path.exists(d):
            print(f"Device not found: {d}")
            sys.exit(1)

    app = DualFeedApp(dev1, dev2)
    app.show_all()
    Gtk.main()

