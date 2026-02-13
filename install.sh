#!/bin/bash
set -e

# Yahboom Jetson Orin Nano CUBE Case Setup
# Installs OLED display, RGB blue cycling, and fan control
# Works with: Jetson Orin Nano (SUB/Official) + CUBE NANO Case

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
USER="$(whoami)"
HOME_DIR="$HOME"

echo "============================================"
echo " Yahboom Jetson Orin Nano CUBE Case Setup"
echo "============================================"
echo "Install dir: $INSTALL_DIR"
echo "User:        $USER"
echo ""

# --- 1. Install system dependencies ---
echo "[1/5] Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-smbus i2c-tools libjpeg-dev zlib1g-dev git

# --- 2. Install Python dependencies ---
echo "[2/5] Installing Python packages..."
pip3 install smbus Adafruit_SSD1306 Pillow setuptools

# --- 3. Install CubeNanoLib driver ---
echo "[3/5] Installing CubeNanoLib driver..."
if python3 -c "from CubeNanoLib import CubeNano" 2>/dev/null; then
    echo "  CubeNanoLib already installed, skipping."
else
    TMPDIR=$(mktemp -d)
    pip3 install gdown 2>/dev/null || true
    GDOWN=$(which gdown 2>/dev/null || echo "$HOME/.local/bin/gdown")
    "$GDOWN" --folder "https://drive.google.com/drive/folders/1A4L1ec-Na1_K0K1LXdnzSCva2iZ02YVX" -O "$TMPDIR/code" 2>&1
    LIBZIP=$(find "$TMPDIR" -name "CubeNanoLib*.zip" | head -1)
    if [ -n "$LIBZIP" ]; then
        cd "$(dirname "$LIBZIP")"
        unzip -o "$LIBZIP"
        cd CubeNanoLib* 2>/dev/null || cd "$(dirname "$LIBZIP")"
        sudo python3 setup.py install
        echo "  CubeNanoLib installed."
    else
        echo "  ERROR: Could not download CubeNanoLib. Download manually from:"
        echo "  https://www.yahboom.net/study/CUBE_NANO"
        exit 1
    fi
    rm -rf "$TMPDIR"
    cd "$INSTALL_DIR"
fi

# --- 4. Detect I2C bus ---
echo "[4/5] Detecting I2C bus..."
I2C_BUS=""
for bus in 7 1 0 8; do
    if python3 -c "
from CubeNanoLib import CubeNano
bot = CubeNano(i2c_bus=$bus)
v = bot.get_Version()
del bot
print(v)
" 2>/dev/null; then
        I2C_BUS=$bus
        echo "  Found CubeNano controller on I2C bus $bus"
        break
    fi
done

if [ -z "$I2C_BUS" ]; then
    echo "  WARNING: CubeNano controller not found on any I2C bus."
    echo "  Check the I2C cable connection from CUBE case to carrier board."
    echo "  Defaulting to bus 7 (Orin Nano standard)."
    I2C_BUS=7
fi

# Update scripts with detected bus
sed -i "s/i2c_bus=[0-9]*/i2c_bus=$I2C_BUS/g" "$INSTALL_DIR/scripts/oled.py"
sed -i "s/i2c_bus=[0-9]*/i2c_bus=$I2C_BUS/g" "$INSTALL_DIR/scripts/rgb_blue.py"

# --- 5. Install systemd services ---
echo "[5/5] Installing systemd services..."

for svc in yahboom_wifi_setup yahboom_oled yahboom_rgb; do
    sed -e "s|__USER__|$USER|g" \
        -e "s|__HOME__|$HOME_DIR|g" \
        -e "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
        "$INSTALL_DIR/services/${svc}.service" | sudo tee "/etc/systemd/system/${svc}.service" > /dev/null
done

sudo systemctl daemon-reload
sudo systemctl enable yahboom_wifi_setup.service yahboom_oled.service yahboom_rgb.service
sudo systemctl restart yahboom_wifi_setup.service yahboom_oled.service yahboom_rgb.service

echo ""
echo "============================================"
echo " Setup complete!"
echo "============================================"
echo ""
echo " OLED:  showing CPU%, temp, RAM, disk, IP"
echo " RGB:   blue cycle breathing"
echo " Fan:   ON"
echo " I2C:   bus $I2C_BUS"
echo " WiFi:  setup portal (hotspot if no network)"
echo ""
echo " Services (auto-start on boot):"
echo "   sudo systemctl status yahboom_wifi_setup"
echo "   sudo systemctl status yahboom_oled"
echo "   sudo systemctl status yahboom_rgb"
echo ""
echo " To switch to headless (no desktop):"
echo "   sudo systemctl set-default multi-user.target"
echo "   sudo reboot"
echo ""
