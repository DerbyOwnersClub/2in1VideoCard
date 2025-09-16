

# ChatGPT ref
https://chatgpt.com/c/68c0d8a1-4a3c-8331-a638-b129179a8af0


# Reset Gstreamer
# cycle clears pads, renegotiates caps, and resets queues without needing to restart the process.
pipeline.set_state(Gst.State.NULL)
pipeline.set_state(Gst.State.READY)
pipeline.set_state(Gst.State.PLAYING)


# del cache
rm -rf ~/.cache/gstreamer-1.0
rm -rf ~/.local/share/gstreamer-1.0


# refresh registry
gst-inspect-1.0 --version
gst-inspect-1.0 | head






