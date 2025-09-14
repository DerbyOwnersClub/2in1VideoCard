import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst, Gtk, GObject

# Initialize GStreamer/GTK
GObject.threads_init()
Gst.init(None)

# Build pipeline with gtksink
pipeline_str = (
    "v4l2src device=/dev/video2 ! image/jpeg,width=1280,height=720,framerate=60/1 ! "
    "jpegdec ! videocrop left=30 right=39 top=0 bottom=0 ! "
    "videoscale ! video/x-raw,width=1280,height=720 ! "
    "videoconvert ! gtksink name=sink"
)

pipeline = Gst.parse_launch(pipeline_str)
sink = pipeline.get_by_name("sink")

# Create GTK window
win = Gtk.Window()
win.set_default_size(1280, 720)
win.set_decorated(False)   # remove titlebar/borders
win.set_position(Gtk.WindowPosition.CENTER)

# Embed the gtksink widget
video_widget = sink.props.widget
win.add(video_widget)

win.connect("destroy", Gtk.main_quit)
win.show_all()

# Start playback
pipeline.set_state(Gst.State.PLAYING)

Gtk.main()
