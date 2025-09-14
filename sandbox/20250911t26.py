import gi
gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gst, Gtk, GObject, Gdk

# Initialize
GObject.threads_init()
Gst.init(None)

def apply_css():
    css = b"""
    #controls {
        background-color: rgba(0, 0, 0, 0.45); /* semi-transparent black bar */
        padding: 6px;
    }
    #controls frame {
        border: 1px solid rgba(255,255,255,0.25);
        border-radius: 6px;
        padding: 4px;
        margin-right: 8px;
    }
    #controls frame label {
        color: white;
    }
    #controls scale {
        min-width: 200px;
    }
    #value-label {
        color: white;
        font-size: 11px;
    }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

class VideoApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Video Preview")
        self.set_default_size(1600, 800)
        self.set_decorated(False)
        self.connect("key-press-event", self.on_key_press)
        self.connect("destroy", self.quit)

        apply_css()

        # Main layout: video on top (expands), controls bar at bottom
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

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

        # Add video (fills remaining space)
        vbox.pack_start(video_widget, True, True, 0)

        # Bottom controls bar (horizontal)
        control_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        control_bar.set_name("controls")
        control_bar.set_halign(Gtk.Align.FILL)
        control_bar.set_valign(Gtk.Align.END)

        # Add sliders to the bottom bar (arranged horizontally)
        self.add_slider(control_bar, "Horizontal (X)", 0, 1920, 0, self.on_horizontal_changed)
        self.add_slider(control_bar, "Vertical (Y)", 0, 1080, 0, self.on_vertical_changed)
        self.add_slider(control_bar, "Crop Left", 0, 200, 0, self.on_crop_left_changed)
        self.add_slider(control_bar, "Crop Right", 0, 200, 0, self.on_crop_right_changed)

        # Put the controls bar at the bottom of the window
        vbox.pack_start(control_bar, False, False, 0)

        # Start pipeline
        self.pipeline.set_state(Gst.State.PLAYING)

    def add_slider(self, parent, label, min_val, max_val, init_val, callback):
        frame = Gtk.Frame(label=label)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        adj = Gtk.Adjustment(init_val, min_val, max_val, 1, 10, 0)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.connect("value-changed", callback)

        value_label = Gtk.Label(label=str(init_val))
        value_label.set_name("value-label")
        scale.value_label = value_label  # store reference

        inner.pack_start(scale, True, True, 0)
        inner.pack_start(value_label, False, False, 0)
        frame.add(inner)

        parent.pack_start(frame, False, False, 0)

    # Slider callbacks (X/Y are placeholders without a compositor)
    def on_horizontal_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        # If you later add a compositor, map this to pad.set_property("xpos", val)

    def on_vertical_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        # If you later add a compositor, map this to pad.set_property("ypos", val)

    def on_crop_left_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        self.cropper.set_property("left", val)

    def on_crop_right_changed(self, scale):
        val = int(scale.get_value())
        scale.value_label.set_text(str(val))
        self.cropper.set_property("right", val)

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.quit()

    def quit(self, *args):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

if __name__ == "__main__":
    app = VideoApp()
    app.show_all()
    Gtk.main()
