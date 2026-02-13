#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
sudo systemctl stop yahboom_oled.service

len1=$(ps -ef | grep oled.py | grep -v grep | wc -l)
echo "Number of processes=$len1"

if [ "$len1" -eq 0 ]; then
    echo "oled.py is not running"
else
    pid_number=$(ps -ef | grep oled.py | grep -v grep | awk '{print $2}')
    kill -9 $pid_number
    echo "oled.py killed, PID: $pid_number"
fi
python3 "$SCRIPT_DIR/oled.py" clear
sleep .1
