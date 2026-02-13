# Yahboom Jetson Orin Nano CUBE Case Setup

Automated setup for the **Yahboom Jetson MINI CUBE NANO Case** on Jetson Orin Nano (SUB/Official).

Configures OLED display, RGB lighting (blue cycle), fan control, and strips the system to a **minimal headless setup optimized for real-time workloads** (e.g., voice-to-text transcription).

## What's Included

| Component | Description |
|-----------|-------------|
| **OLED Display** | Shows CPU usage, CPU temperature, RAM, disk, and local IP |
| **RGB Lighting** | Blue cycle breathing effect (hardware-driven, no flicker) |
| **Fan Control** | Auto-on at boot |
| **Headless Mode** | Disables desktop GUI, saves ~145MB RAM |
| **System Minimizer** | Strips 35+ unnecessary services, removes snapd, sets max performance clocks |

## Compatible Hardware

- Yahboom Jetson Orin Nano 8GB/4GB (SUB or Official)
- Jetson MINI CUBE NANO Case (with OLED, RGB light bar, cooling fan)
- Tested on JetPack 5.x / Ubuntu 22.04

## Quick Install

SSH into your Jetson and run:

```bash
git clone https://github.com/hasanmullahadi/JetsonOrinNanoYahboom.git
cd JetsonOrinNanoYahboom
chmod +x install.sh
./install.sh
```

The installer will:
1. Install system and Python dependencies
2. Download and install CubeNanoLib driver
3. Auto-detect the correct I2C bus
4. Install and enable systemd services (auto-start on boot)

## Minimal Headless Setup (Recommended)

For dedicated real-time workloads, run the minimizer to strip the system down:

```bash
chmod +x scripts/minimize.sh
sudo ./scripts/minimize.sh
sudo reboot
```

This disables 35+ unnecessary services (Bluetooth, printing, snap, modem, firmware updates, desktop compositors), removes all snap packages (Chromium, CUPS, GNOME), and locks CPU/GPU/EMC to max clocks via `jetson_clocks`.

**Before:** ~670 MB RAM used (with desktop)
**After:** ~430 MB RAM used — **~6.8 GB free** for your workload

To restore the GUI later:
```bash
sudo systemctl set-default graphical.target
sudo reboot
```

## Service Commands

```bash
# OLED display
sudo systemctl start/stop/restart/status yahboom_oled

# RGB + fan
sudo systemctl start/stop/restart/status yahboom_rgb
```

## OLED Display Layout

```
CPU:XX%    48.1C
RAM:XX% -> 7.4GB
SDC:XX% -> 234GB
IP:192.168.x.x
```

## CubeNanoLib API Reference

```python
from CubeNanoLib import CubeNano
bot = CubeNano(i2c_bus=7)  # bus 7 for Orin Nano, bus 1 for Jetson Nano

# Fan
bot.set_Fan(1)              # 0=Off, 1=On

# RGB preset effects
bot.set_RGB_Effect(6)       # 0=Off, 1=Breathing, 2=Marquee, 3=Rainbow,
                            # 4=Dazzle, 5=Running, 6=Cycle breathing
bot.set_RGB_Color(2)        # 0=Red, 1=Green, 2=Blue, 3=Yellow,
                            # 4=Purple, 5=Cyan, 6=White
bot.set_RGB_Speed(2)        # 1=Slow, 2=Medium, 3=Fast

# Individual LED control (14 LEDs: index 0-13, or 255=all)
bot.set_Single_Color(255, 0, 0, 255)  # All LEDs blue

del bot
```

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## File Structure

```
.
├── CLAUDE.md               # Claude Code AI assistant instructions & technical reference
├── install.sh              # One-command setup script
├── uninstall.sh            # Remove services, turn off RGB/OLED
├── scripts/
│   ├── oled.py             # OLED display (CPU, temp, RAM, disk, IP)
│   ├── rgb_blue.py         # RGB blue cycle + fan on
│   ├── kill_oled.sh        # Stop OLED and clear display
│   └── minimize.sh         # Strip system to bare minimum for real-time workloads
└── services/
    ├── yahboom_oled.service
    └── yahboom_rgb.service
```

## Claude Code

This repo includes a [`CLAUDE.md`](CLAUDE.md) file with detailed technical context for [Claude Code](https://claude.com/claude-code). It covers hardware details, I2C bus configuration, CubeNanoLib API, headless setup, and troubleshooting — so Claude can help modify or debug this project with full context.

## Resources

- [Yahboom CUBE Case Docs](https://www.yahboom.net/study/CUBE_NANO)
- [Yahboom GitHub - Jetson CUBE Case](https://github.com/YahboomTechnology/Jetson-CUBE-case)
- [CubeNanoLib Install Guide](https://www.yahboom.net/public/upload/upload-html/1690165945/1.%20Install%20CubeNano%20driver%20library.html)
