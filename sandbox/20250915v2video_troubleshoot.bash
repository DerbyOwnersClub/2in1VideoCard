#
# Purpose:
# To identify supported types of videos
# ref chatgpt - https://chatgpt.com/c/68c5d7e4-861c-8330-9320-3dd8f65bc457
#
#
# Author:
# 20250TFR - 
#!/bin/bash


# LOGFILE="video_test_$(date +%Y%m%d-%H%M).log"
LOGFILE="video_test.log"

REPORT=""


echo "=== Video Troubleshoot Log ===" | tee "$LOGFILE"
echo "Timestamp: $(date)" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

echo "Device Number: $dev"| tee -a  "$LOGFILE"

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

  # Set default of no at top of loop
  DEVICE_WORKED="no"
  
  echo " Default Device Worked value is $DEVICE_WORKED"| tee -a  "$LOGFILE"


# ffplay MJPEG tests
# Test at 60 fps
  for res in 1920x1080 1280x720 640x480; do
    echo "--- ffplay MJPEG $res 30fps ---" | tee -a "$LOGFILE"
    timeout 5 ffplay -hide_banner -loglevel error \
      -f v4l2 -input_format mjpeg -framerate 30 -video_size $res "$dev" \
      >>"$LOGFILE" 2>&1

  echo "1920x1080 Device Worked value is $DEVICE_WORKED"| tee -a  "$LOGFILE"

    if [ $? -eq 0 ]; then
      DEVICE_WORKED="yes"
    fi
  done


  # ffplay YUYV test
  echo "--- ffplay YUYV 640x480 10fps ---" | tee -a "$LOGFILE"
  timeout 5 ffplay -hide_banner -loglevel error \
    -f v4l2 -input_format yuyv422 -framerate 10 -video_size 640x480 "$dev" \
    >>"$LOGFILE" 2>&1
  if [ $? -eq 0 ]; then
    DEVICE_WORKED="yes"
  fi



  # GStreamer MJPEG test
  echo "--- GStreamer MJPEG test ---" | tee -a "$LOGFILE"
  timeout 5 gst-launch-1.0 v4l2src device="$dev" ! jpegdec ! fakesink \
    >>"$LOGFILE" 2>&1
  if [ $? -eq 0 ]; then
    DEVICE_WORKED="yes"
  fi

  # GStreamer H.264 test
  echo "--- GStreamer H.264 test ---" | tee -a "$LOGFILE"
  timeout 5 gst-launch-1.0 v4l2src device="$dev" ! h264parse ! avdec_h264 ! fakesink \
    >>"$LOGFILE" 2>&1
  if [ $? -eq 0 ]; then
    DEVICE_WORKED="yes"
  fi


  # Build report summary

echo "Before reporting Device Number: $dev"
echo $DEVICE_WORKED

  if [ "$DEVICE_WORKED" == "yes" ]; then
    REPORT+="Device $dev → ✅ WORKING\n"
    echo "Added to report array Device_Worked = yes"

  else

    REPORT+="Device $dev → ❌ NO VALID VIDEO\n"
    echo " Device_Failed to work"
    echo "Value of Device name is $dev DEVICE failed. Device_worked val is -  $DEVICE_WORKED"
  fi

  echo "After reporting Device Number: $dev"
  echo $DEVICE_WORKED

  echo "" | tee -a "$LOGFILE"
done

echo "=== Troubleshoot Complete. Log saved to $LOGFILE ==="
echo -e "\n=== Report Summary ==="
echo -e "$REPORT"
