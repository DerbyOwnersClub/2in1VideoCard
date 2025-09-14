import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst, Gtk, GObject

# Initialize
GObject.threads_init()
Gst.init(None)

class VideoApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Video Preview")
        self.set_default_size(1600, 800)
        self.set_decorated(False)

        # Main layout: video on left, controls on right
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(hbox)

        # Video sink
        self.pipeline = Gst.parse_launch(
            "v4l2src device=/dev/video2 ! image/jpeg,width=1280,height=720,framerate=60/1 ! "
            "jpegdec ! videocrop name=cropper left=0 right=0 top=0 bottom=0 ! "
            "videoscale ! video/x-raw,width=1280,height=720 ! "
            "videoconvert ! gtksink name=sink"
        )
        self.cropper = self.pipeline.get_by_name("cropper")
        sink = self.pipeline.get_by_name("sink")
        video_widget = sink.props.widget

        # Add video widget
        hbox.pack_start(video_widget, True, True, 0)

        # Control panel
        control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hbox.pack_start(control_box, False, False, 10)

        # Sliders
        self.add_slider(control_box, "Horizontal (X)", 0, 1920, 0, self.on_horizontal_changed)
        self.add_slider(control_box, "Vertical (Y)", 0, 1080, 0, self.on_vertical_changed)
        self.add_slider(control_box, "Crop Left", 0, 200, 0, self.on_crop_left_changed)
        self.add_slider(control_box, "Crop Right", 0, 200, 0, self.on_crop_right_changed)

        # Start pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

        self.connect("destroy", self.quit)

    def add_slider(self, parent, label, min_val, max_val, init_val, callback):
        frame = Gtk.Frame(label=label)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        frame.add(vbox)

        # Slider
        adj = Gtk.Adjustment(init_val, min_val, max_val, 1, 10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.connect("value-changed", callback)

        # Label for value
        value_label = Gtk.Label(label=str(init_val))
        scale.value_label = value_label  # store reference

        vbox.pack_start(scale, True, True, 0)
        vbox.pack_start(value_label, False, False, 0)
        parent.pack_start(frame, False, False, 0)

    # Slider callbacks
    def on_horizontal_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        # Here you’d move compositor xpos — not used in single-feed example

    def on_vertical_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        # Here you’d move compositor ypos — not used in single-feed example

    def on_crop_left_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        self.cropper.set_property("left", val)

    def on_crop_right_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        self.cropper.set_property("right", val)

    def quit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

if __name__ == "__main__":
    app = VideoApp()
    app.show_all()
    Gtk.main()
