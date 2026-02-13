# Jetson Orin Nano + Yahboom CUBE Case — Claude Code Instructions

## Project Overview

This repo configures the **Yahboom Jetson MINI CUBE NANO Case** (OLED, RGB, fan) on Jetson Orin Nano and sets up a **minimal headless system optimized for real-time voice-to-text transcription**. All scripts are meant to run directly on the Jetson over SSH.

## Hardware

- **Board:** Jetson Orin Nano 4GB/8GB (SUB or Official), JetPack 5.x / Ubuntu 22.04
- **Case:** Yahboom MINI CUBE NANO Case
- **Peripherals:** SSD1306 OLED (128x32), 14-LED RGB light bar, cooling fan
- **I2C:** CubeNano controller at address `0x0E`. Bus 7 on Orin Nano DevKit/SUB, bus 1 on Jetson Nano. The install script auto-detects.

## Headless Setup

The Jetson Orin Nano ships with GNOME desktop enabled by default. For headless (SSH-only) operation, disable the GUI to save ~145 MB RAM:

```bash
# Switch to headless (CLI only, persists across reboots)
sudo systemctl set-default multi-user.target

# Stop the desktop immediately without rebooting
sudo systemctl stop gdm

# To restore the desktop later
sudo systemctl set-default graphical.target
sudo systemctl start gdm
```

After switching to headless, the Jetson is accessible only via SSH. The OLED display on the CUBE case will show the device IP for easy discovery.

## Repo Structure

```
scripts/
  oled.py          — OLED display: CPU%, CPU temp, RAM, disk, IP (line 1-4)
  rgb_blue.py      — Sets RGB to blue cycle breathing + fan on
  wifi_setup.py    — WiFi setup portal: hotspot + web config if no network
  kill_oled.sh     — Stops OLED service and clears the display
  minimize.sh      — Strips system to bare minimum for real-time workloads
services/
  yahboom_oled.service       — systemd unit for OLED (auto-start on boot)
  yahboom_rgb.service        — systemd unit for RGB + fan (auto-start on boot)
  yahboom_wifi_setup.service — systemd unit for WiFi setup portal
install.sh         — Full setup: dependencies, driver, I2C detection, services
uninstall.sh       — Remove services, turn off RGB, clear OLED
```

## Key Technical Details

- **OLED** uses `Adafruit_SSD1306` library with a 128x32 SSD1306 display over I2C
- **CPU temp** is read from `/sys/devices/virtual/thermal/thermal_zone0/temp` (millidegrees)
- **RGB effects** are hardware-driven by the CubeNano microcontroller (no flicker). Use `set_RGB_Effect()` + `set_RGB_Color()` for smooth animations. Avoid per-LED `set_Single_Color()` in fast loops — it causes visible flickering due to I2C overhead.
- **CubeNanoLib** is installed via `setup.py` from Yahboom's Google Drive. The install script handles this automatically.
- **Network interfaces** on Yahboom SUB carrier board: `wlP1p1s0` (WiFi), `enP8p1s0` (Ethernet). The oled.py script checks both for IP display.
- **Service files** use `__USER__`, `__HOME__`, `__INSTALL_DIR__` placeholders — `install.sh` substitutes them at install time.

## CubeNanoLib API Quick Reference

```python
from CubeNanoLib import CubeNano
bot = CubeNano(i2c_bus=7)

bot.set_Fan(state)                      # 0=Off, 1=On
bot.set_RGB_Effect(effect)              # 0=Off, 1=Breathing, 2=Marquee, 3=Rainbow,
                                        # 4=Dazzle, 5=Running, 6=Cycle breathing
bot.set_RGB_Color(color)                # 0=Red, 1=Green, 2=Blue, 3=Yellow,
                                        # 4=Purple, 5=Cyan, 6=White
bot.set_RGB_Speed(speed)                # 1=Slow, 2=Medium, 3=Fast
bot.set_Single_Color(index, r, g, b)    # index 0-13 per LED, 255=all
bot.get_Version()                       # Returns firmware version int

del bot
```

## Common Tasks

**Modify OLED layout:** Edit `scripts/oled.py` — the `main_program()` method controls what's shown on each of the 4 lines (8px each). After editing, restart: `sudo systemctl restart yahboom_oled`

**Change RGB color/effect:** Edit `scripts/rgb_blue.py` and restart: `sudo systemctl restart yahboom_rgb`

**Troubleshoot I2C:** Run `sudo i2cdetect -y 7` (or bus 1). The CubeNano controller should appear at `0x0e`. The OLED at `0x3c`. If missing, check the ribbon cable from the CUBE case to the carrier board.

## WiFi Setup Portal

If the Jetson can't connect to WiFi on boot (e.g., deployed to a new location), it automatically creates a hotspot for configuration:

1. On boot, `wifi_setup.py` waits 15s for WiFi to connect
2. **If connected** → exits immediately (zero overhead in normal operation)
3. **If not connected** → creates hotspot `JetsonSetup` (password `jetson1234`) on `10.42.0.1`
4. User connects phone/laptop to hotspot, opens `10.42.0.1` in browser
5. Web page lists available WiFi networks with signal strength
6. User selects network, enters password, submits
7. Jetson stops hotspot, connects to selected network, web server shuts down

**Key details:**
- Hotspot uses NetworkManager: `nmcli device wifi hotspot ifname wlP1p1s0 ssid JetsonSetup password jetson1234`
- Web server is Python `http.server` (no dependencies beyond stdlib)
- WiFi scan: `nmcli -t -f SSID,SIGNAL,SECURITY device wifi list`
- Service runs as root (needed for nmcli network control), `Type=simple` with 300s timeout
- Runs `Before=yahboom_oled.service` so OLED shows the correct IP after connection

**To test:** `nmcli connection delete "<your-wifi>"` then reboot. The hotspot should appear.

## Minimal System for Real-Time Workloads

Run `scripts/minimize.sh` to strip the system down for dedicated real-time tasks (e.g., voice-to-text transcription). This:

- Switches to headless (`multi-user.target`)
- Disables 35+ unnecessary services (Bluetooth, printing, snap, modem, firmware updates, desktop compositors, etc.)
- Removes snapd and all snap packages (Chromium, CUPS, GNOME, etc.)
- Masks fwupd and packagekit to prevent them from restarting
- Enables `jetson_clocks` at boot for max CPU/GPU/EMC clock speeds

**What remains running after minimize:**
- SSH, WiFi (NetworkManager + wpa_supplicant)
- NVIDIA runtime (nvpmodel, nvpower, nvcpupowerfix, nvphs, nvzramconfig)
- PulseAudio (needed for audio input)
- OLED + RGB services
- systemd essentials (journald, resolved, timesyncd, cron)

**Memory footprint:** ~430 MB used (down from ~670 MB with desktop), leaving ~6.8 GB available for inference workloads.

**Performance mode:** 15W with `jetson_clocks` locks all CPU/GPU/EMC to max frequencies — no dynamic scaling overhead during inference.
