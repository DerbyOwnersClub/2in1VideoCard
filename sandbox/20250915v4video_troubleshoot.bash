#
# Purpose:
# To test available video resources with gstream 
# and provide the results on the console and in a log file named
# video_test.log.
#
# Summary: 
# Video devices are enumerated and cycled thru with different tests.
# Video is attempted to be displayed in different formats discovered 
# and the operator is prompted to answer y or n if video is seen on the screen.
# There is a log file written during execution and a summary written to the console
# at the end of execution.
#
#
# Requirements:
# Unix based operating system.
# BASH shell script
# Hardware to capture video
# Software - Gstream installation
#
#-----------------------------------------------------------------------------------
# Revision History
#-----------------------------------------------------------------------------------
# Date         | Author                            | Description
#-----------------------------------------------------------------------------------
# 20250912  | TFR                   | Maker
#
#
#-----------------------------------------------------------------------------------

#!/bin/bash

LOGFILE="video_test_$(date +%Y%m%d-%H%M).log"
REPORT=""

echo "=== Video Troubleshoot Log ===" | tee "$LOGFILE"
echo "Timestamp: $(date)" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

DEVICES=$(ls /dev/video* 2>/dev/null)

if [ -z "$DEVICES" ]; then
  echo "No /dev/video* devices found." | tee -a "$LOGFILE"
  exit 1
fi

# Loop thru found devices
for dev in $DEVICES; do
  echo "===== Device: $dev =====" | tee -a "$LOGFILE"
  echo " "
  
  # List capabilities
  echo "--- v4l2-ctl formats ---" | tee -a "$LOGFILE"
  v4l2-ctl --device="$dev" --list-formats-ext 2>&1 | tee -a "$LOGFILE"

  DEVICE_WORKED="no"

  ## ffplay MJPEG tests
  for res in 1920x1080 1280x720 640x480; do
    echo "--- ffplay MJPEG $res 30fps ---" | tee -a "$LOGFILE"
    timeout 5 ffplay -hide_banner -loglevel error \
      -f v4l2 -input_format mjpeg -framerate 30 -video_size $res "$dev" \
      >>"$LOGFILE" 2>&1
   
    read -n 1 -r -p "Did you see video for $dev at $res (MJPEG 30fps)? (y/n): " answer
    echo
    if [[ "$answer" =~ ^[Yy]$ ]]; then
      DEVICE_WORKED="yes"
    fi
  done

  ## ffplay YUYV test
  echo "--- ffplay YUYV 640x480 10fps ---" | tee -a "$LOGFILE"
  timeout 5 ffplay -hide_banner -loglevel error \
    -f v4l2 -input_format yuyv422 -framerate 10 -video_size 640x480 "$dev" \
    >>"$LOGFILE" 2>&1

  read -n 1 -r -p "Did you see video for $dev at 640x480 (YUYV 10fps)? (y/n): " answer
  echo
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    DEVICE_WORKED="yes"
  fi

  ## GStreamer MJPEG test
  echo "--- GStreamer MJPEG test ---" | tee -a "$LOGFILE"
  timeout 5 gst-launch-1.0 v4l2src device="$dev" ! jpegdec ! fakesink \
    >>"$LOGFILE" 2>&1

  read -n 1 -r -p "Did you see video for $dev (GStreamer MJPEG)? (y/n): " answer
  echo
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    DEVICE_WORKED="yes"
  fi

  ## GStreamer H.264 test
  echo "--- GStreamer H.264 test ---" | tee -a "$LOGFILE"
  timeout 5 gst-launch-1.0 v4l2src device="$dev" ! h264parse ! avdec_h264 ! fakesink \
    >>"$LOGFILE" 2>&1

  read -n 1 -r -p "Did you see video for $dev (GStreamer H.264)? (y/n): " answer
  echo
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    DEVICE_WORKED="yes"
  fi

  ## Build report summary
  if [ "$DEVICE_WORKED" == "yes" ]; then
    REPORT+="Device $dev → ✅ WORKING\n"
  else
    REPORT+="Device $dev → ❌ NO VALID VIDEO\n"
  fi

  echo "" | tee -a "$LOGFILE"
done

echo "=== Troubleshoot Complete. Log saved to $LOGFILE ==="
echo -e "\n=== Report Summary ==="
echo -e "$REPORT"
