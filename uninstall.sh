#!/bin/bash
set -e

echo "Stopping and removing Yahboom services..."

sudo systemctl stop yahboom_oled.service 2>/dev/null || true
sudo systemctl stop yahboom_rgb.service 2>/dev/null || true
sudo systemctl disable yahboom_oled.service 2>/dev/null || true
sudo systemctl disable yahboom_rgb.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/yahboom_oled.service
sudo rm -f /etc/systemd/system/yahboom_rgb.service
sudo systemctl daemon-reload

# Clear OLED
python3 "$(dirname "$0")/scripts/oled.py" clear 2>/dev/null || true

# Turn off RGB
python3 -c "
from CubeNanoLib import CubeNano
bot = CubeNano(i2c_bus=7)
bot.set_RGB_Effect(0)
bot.set_Fan(0)
del bot
" 2>/dev/null || true

echo "Done. Services removed, OLED cleared, RGB off."
