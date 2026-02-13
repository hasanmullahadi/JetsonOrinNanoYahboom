#!/bin/bash
set -e

# Strip Jetson Orin Nano to minimal headless for real-time workloads
# Keeps: SSH, WiFi, NVIDIA runtime, PulseAudio (audio input), OLED/RGB
# Removes: Desktop, Bluetooth, printing, snap, modem, firmware updates

echo "============================================"
echo " Jetson Orin Nano — Minimal Headless Setup"
echo "============================================"
echo ""

# --- 1. Switch to headless ---
echo "[1/5] Switching to headless mode..."
sudo systemctl set-default multi-user.target
sudo systemctl stop gdm 2>/dev/null || true

# --- 2. Disable unnecessary services ---
echo "[2/5] Disabling unnecessary services..."
DISABLE_SERVICES=(
  bluetooth.service
  ModemManager.service
  avahi-daemon.service
  snap.cups.cupsd.service
  snap.cups.cups-browsed.service
  accounts-daemon.service
  switcheroo-control.service
  udisks2.service
  power-profiles-daemon.service
  kerneloops.service
  openvpn.service
  sssd.service
  rpcbind.service
  seatd.service
  nvweston.service
  colord.service
  binfmt-support.service
  secureboot-db.service
  ua-reboot-cmds.service
  ubuntu-advantage.service
  e2scrub_reap.service
  anacron.service
  fwupd.service
  packagekit.service
  networkd-dispatcher.service
  systemd-oomd.service
  nvargus-daemon.service
  nvfb.service
  nvfb-early.service
  nvfb-udev.service
  setvtrgb.service
  keyboard-setup.service
  console-setup.service
  nvgetty.service
  nvmefc-boot-connections.service
  nvmf-autoconnect.service
)

for svc in "${DISABLE_SERVICES[@]}"; do
  sudo systemctl stop "$svc" 2>/dev/null || true
  sudo systemctl disable "$svc" 2>/dev/null || true
done

sudo systemctl mask fwupd.service packagekit.service 2>/dev/null || true
echo "  Disabled ${#DISABLE_SERVICES[@]} services"

# --- 3. Disable and remove snapd ---
echo "[3/5] Removing snapd and snap packages..."
if command -v snap &>/dev/null; then
  SNAPS=$(snap list 2>/dev/null | awk 'NR>1{print $1}' | grep -v snapd || true)
  for pkg in $SNAPS; do
    sudo snap remove --purge "$pkg" 2>/dev/null || true
  done
  sudo snap remove --purge snapd 2>/dev/null || true
  sudo apt-get purge -y -qq snapd 2>/dev/null || true
  echo "  Snapd removed"
else
  echo "  Snapd already removed"
fi

# --- 4. Disable snap-related services ---
echo "[4/5] Disabling snap services..."
for svc in snapd.service snapd.socket snapd.apparmor.service snapd.seeded.service \
           snapd.autoimport.service snapd.core-fixup.service \
           snapd.recovery-chooser-trigger.service snapd.system-shutdown.service; do
  sudo systemctl stop "$svc" 2>/dev/null || true
  sudo systemctl disable "$svc" 2>/dev/null || true
done

# --- 5. Set max performance ---
echo "[5/5] Setting max performance clocks..."
sudo jetson_clocks 2>/dev/null || true

# Create jetson_clocks boot service
sudo bash -c 'cat > /etc/systemd/system/jetson-clocks.service << EOF
[Unit]
Description=Maximize Jetson clocks for real-time performance
After=nvpmodel.service

[Service]
Type=oneshot
ExecStart=/usr/bin/jetson_clocks
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl daemon-reload
sudo systemctl enable jetson-clocks.service 2>/dev/null

echo ""
echo "============================================"
echo " Minimal headless setup complete!"
echo "============================================"
echo ""
free -h
echo ""
echo "Reboot recommended: sudo reboot"
echo ""
