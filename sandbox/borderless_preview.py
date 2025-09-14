import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from gi.repository import Gtk, Gst, GstVideo, GdkX11

Gst.init(None)
Gtk.init(None)

class BorderlessVideoWindow(Gtk.Window):
    def __init__(self):
        super().__init__()

        # No title bar or border
        self.set_decorated(False)

        # Set window size to video resolution
        self.set_default_size(1280, 720)

        # Position top-left of screen
        self.move(0, 50)

        # Drawing area for video
        self.drawing_area = Gtk.DrawingArea()
        self.add(self.drawing_area)
        self.show_all()

        # GStreamer pipeline (your working one, as-is)
        self.pipeline = Gst.parse_launch("""
            v4l2src device=/dev/video2 ! image/jpeg, width=1280, height=720, framerate=60/1 !
            jpegdec ! videoconvert ! video/x-raw,format=RGBA ! queue !
            compositor name=comp sink_0::xpos=0 sink_0::ypos=0 !
            videoconvert ! xvimagesink name=vsink
        """)

        self.vsink = self.pipeline.get_by_name("vsink")

        # Attach sink to GTK window
        bus = self.pipeline.get_bus()
        bus.enable_sync_message_emission()
        bus.connect("sync-message::element", self.on_sync_message)

        # Start video
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_sync_message(self, bus, message):
        if message.get_structure() and message.get_structure().get_name() == "prepare-window-handle":
            sink = message.src
            if hasattr(self.drawing_area, 'get_window'):
                window = self.drawing_area.get_window()
                if window:
                    sink.set_window_handle(window.get_xid())

win = BorderlessVideoWindow()
Gtk.main()
