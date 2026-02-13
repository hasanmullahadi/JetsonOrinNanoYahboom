#!/usr/bin/env python3
"""WiFi Setup Portal for Jetson Orin Nano.

On boot: waits for WiFi to connect. If it doesn't connect within 15s,
creates a hotspot (JetsonSetup / jetson1234) and serves a web page at
10.42.0.1 where the user can select a WiFi network and enter credentials.
"""

import subprocess
import time
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

WIFI_IFACE = "wlP1p1s0"
HOTSPOT_SSID = "JetsonSetup"
HOTSPOT_PASS = "jetson1234"
HOTSPOT_IP = "10.42.0.1"
HOTSPOT_CON_NAME = "JetsonSetup-Hotspot"
WAIT_TIMEOUT = 15
WEB_PORT = 80
FLAG_FILE = "/tmp/wifi_setup_active"

# Cached network list (scan must happen while not in AP mode)
cached_networks = []


# ---------------------------------------------------------------------------
# WiFi helpers
# ---------------------------------------------------------------------------

def run(cmd):
    """Run a shell command and return (returncode, stdout)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def wifi_is_connected():
    """Return True if the WiFi interface has an active connection."""
    rc, out = run(f"nmcli -t -f DEVICE,STATE device | grep '^{WIFI_IFACE}:'")
    return ":connected" in out


def wait_for_wifi(timeout=WAIT_TIMEOUT):
    """Poll every 2s for up to timeout seconds. Return True if connected."""
    elapsed = 0
    while elapsed < timeout:
        if wifi_is_connected():
            return True
        time.sleep(2)
        elapsed += 2
    return False


def start_hotspot():
    """Create a WiFi hotspot using NetworkManager."""
    # Delete any stale hotspot connection
    run(f"nmcli connection delete '{HOTSPOT_CON_NAME}' 2>/dev/null")
    rc, out = run(
        f"nmcli device wifi hotspot ifname {WIFI_IFACE} "
        f"con-name '{HOTSPOT_CON_NAME}' "
        f"ssid {HOTSPOT_SSID} password {HOTSPOT_PASS}"
    )
    if rc != 0:
        print(f"[wifi_setup] hotspot failed: {out}", file=sys.stderr)
        return False
    # Signal OLED to show setup instructions
    with open(FLAG_FILE, "w") as f:
        f.write(HOTSPOT_IP)
    print(f"[wifi_setup] hotspot '{HOTSPOT_SSID}' active on {HOTSPOT_IP}")
    return True


def stop_hotspot():
    """Tear down the hotspot connection."""
    # Remove OLED flag
    try:
        os.remove(FLAG_FILE)
    except FileNotFoundError:
        pass
    run(f"nmcli connection down '{HOTSPOT_CON_NAME}' 2>/dev/null")
    run(f"nmcli connection delete '{HOTSPOT_CON_NAME}' 2>/dev/null")


def scan_networks():
    """Scan for WiFi networks. Must be called when NOT in AP/hotspot mode."""
    global cached_networks
    run(f"nmcli device wifi rescan ifname {WIFI_IFACE} 2>/dev/null")
    time.sleep(2)
    _, out = run("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
    networks = {}
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        ssid = parts[0].strip()
        if not ssid or ssid == HOTSPOT_SSID:
            continue
        signal = parts[1].strip()
        security = parts[2].strip()
        # Keep the strongest signal per SSID
        if ssid not in networks or int(signal) > int(networks[ssid]["signal"]):
            networks[ssid] = {"ssid": ssid, "signal": signal, "security": security}
    # Sort by signal strength descending
    cached_networks = sorted(networks.values(), key=lambda n: int(n["signal"]), reverse=True)
    return cached_networks


def rescan_networks():
    """Stop hotspot, scan, restart hotspot. Returns updated network list."""
    print("[wifi_setup] rescan: stopping hotspot temporarily...")
    stop_hotspot()
    time.sleep(2)
    results = scan_networks()
    print(f"[wifi_setup] rescan: found {len(results)} networks, restarting hotspot...")
    start_hotspot()
    time.sleep(2)
    return results


def connect_wifi(ssid, password):
    """Stop hotspot and connect to the given WiFi network. Return (ok, msg)."""
    stop_hotspot()
    time.sleep(2)
    rc, out = run(
        f'nmcli device wifi connect "{ssid}" password "{password}" ifname {WIFI_IFACE}'
    )
    if rc == 0:
        # Wait a moment for IP assignment
        time.sleep(3)
        _, ip_out = run(
            f"nmcli -t -f IP4.ADDRESS device show {WIFI_IFACE} | head -1"
        )
        ip = ip_out.split(":")[-1].split("/")[0] if ip_out else "unknown"
        return True, f"Connected to {ssid} — IP: {ip}"
    else:
        # Reconnect hotspot so user can retry
        start_hotspot()
        return False, f"Failed to connect: {out}"


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jetson WiFi Setup</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
  .card { background: #1e293b; border-radius: 12px; padding: 2rem; width: 90%; max-width: 420px; box-shadow: 0 4px 24px rgba(0,0,0,.4); }
  h1 { font-size: 1.3rem; margin-bottom: 1.2rem; color: #38bdf8; }
  label { display: block; font-size: .85rem; margin-bottom: .3rem; color: #94a3b8; }
  select, #password { width: 100%; padding: .6rem .8rem; border: 1px solid #334155; border-radius: 8px; background: #0f172a; color: #e2e8f0; font-size: 1rem; margin-bottom: 1rem; }
  .net-info { font-size: .75rem; color: #64748b; margin-top: -0.7rem; margin-bottom: 1rem; }
  button { width: 100%; padding: .7rem; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
  .btn-primary { background: #38bdf8; color: #0f172a; }
  .btn-primary:hover { background: #7dd3fc; }
  .btn-secondary { background: #334155; color: #94a3b8; margin-top: .5rem; }
  .btn-secondary:hover { background: #475569; }
  #status { margin-top: 1rem; padding: .8rem; border-radius: 8px; display: none; font-size: .9rem; }
  .success { background: #064e3b; color: #6ee7b7; display: block !important; }
  .error { background: #7f1d1d; color: #fca5a5; display: block !important; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #38bdf8; border-top-color: transparent; border-radius: 50%; animation: spin .6s linear infinite; vertical-align: middle; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="card">
  <h1>Jetson WiFi Setup</h1>
  <form id="form" method="POST" action="/connect">
    <label for="ssid">Network</label>
    <select name="ssid" id="ssid">
      {options}
    </select>
    <div class="net-info" id="net-info"></div>
    <label for="password">Password</label>
    <input type="password" name="password" id="password" placeholder="Enter WiFi password" required>
    <label style="display:flex;align-items:center;gap:.4rem;margin-top:-.5rem;margin-bottom:1rem;cursor:pointer"><input type="checkbox" id="show-pass" style="width:auto;margin:0"> Show password</label>
    <button type="submit" class="btn-primary" id="submit-btn">Connect</button>
  </form>
  <button class="btn-secondary" onclick="rescan()">Rescan Networks</button>
  <div id="status"></div>
</div>
<script>
const nets = {networks_json};
const sel = document.getElementById('ssid');
const info = document.getElementById('net-info');
function updateInfo() {
  const n = nets[sel.value];
  if (n) info.textContent = 'Signal: ' + n.signal + '%  |  Security: ' + n.security;
}
sel.addEventListener('change', updateInfo);
updateInfo();
document.getElementById('show-pass').addEventListener('change', function() {
  document.getElementById('password').type = this.checked ? 'text' : 'password';
});

document.getElementById('form').addEventListener('submit', function(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const st = document.getElementById('status');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Connecting...';
  st.className = ''; st.style.display = 'none';
  fetch('/connect', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'ssid=' + encodeURIComponent(sel.value) + '&password=' + encodeURIComponent(document.getElementById('password').value)
  }).then(r => r.json()).then(d => {
    st.textContent = d.message;
    st.className = d.ok ? 'success' : 'error';
    btn.disabled = false;
    btn.textContent = 'Connect';
  }).catch(() => {
    st.textContent = 'Connection lost — if the Jetson connected successfully, check the OLED for its new IP.';
    st.className = 'success';
    btn.disabled = false;
    btn.textContent = 'Connect';
  });
});

function rescan() {
  const btn = event.target;
  btn.disabled = true; btn.textContent = 'Scanning...';
  fetch('/scan').then(r => r.json()).then(data => {
    sel.innerHTML = '';
    Object.keys(nets).forEach(k => delete nets[k]);
    data.forEach(n => {
      nets[n.ssid] = n;
      const o = document.createElement('option');
      o.value = n.ssid; o.textContent = n.ssid + ' (' + n.signal + '%)';
      sel.appendChild(o);
    });
    updateInfo();
    btn.disabled = false; btn.textContent = 'Rescan Networks';
  }).catch(() => { btn.disabled = false; btn.textContent = 'Rescan Networks'; });
}
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------

class WifiHandler(BaseHTTPRequestHandler):
    server_should_stop = False
    connected_ok = False

    def log_message(self, fmt, *args):
        print(f"[wifi_setup] {args[0]}")

    def do_GET(self):
        if self.path == "/scan":
            self._handle_scan()
        else:
            self._handle_index()

    def do_POST(self):
        if self.path == "/connect":
            self._handle_connect()
        else:
            self.send_error(404)

    def _handle_index(self):
        networks = cached_networks
        options = "\n".join(
            f'<option value="{n["ssid"]}">{n["ssid"]} ({n["signal"]}%)</option>'
            for n in networks
        )
        nets_json = json.dumps({n["ssid"]: n for n in networks})
        html = HTML_PAGE.replace("{options}", options).replace("{networks_json}", nets_json)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _handle_scan(self):
        networks = rescan_networks()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(networks).encode())

    def _handle_connect(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        params = parse_qs(body)
        ssid = params.get("ssid", [""])[0]
        password = params.get("password", [""])[0]

        if not ssid or not password:
            self._json_response(False, "SSID and password are required.")
            return

        print(f"[wifi_setup] connecting to '{ssid}'...")
        ok, msg = connect_wifi(ssid, password)
        self._json_response(ok, msg)

        if ok:
            WifiHandler.connected_ok = True
            WifiHandler.server_should_stop = True

    def _json_response(self, ok, message):
        data = json.dumps({"ok": ok, "message": message})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data.encode())


class StoppableHTTPServer(HTTPServer):
    def service_actions(self):
        if WifiHandler.server_should_stop:
            raise KeyboardInterrupt


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("[wifi_setup] waiting for WiFi connection...")
    if wait_for_wifi():
        print("[wifi_setup] WiFi already connected. Exiting.")
        return

    print("[wifi_setup] no WiFi connection. Scanning for networks...")
    scan_networks()
    print(f"[wifi_setup] found {len(cached_networks)} networks. Starting hotspot...")
    if not start_hotspot():
        print("[wifi_setup] failed to start hotspot. Exiting.", file=sys.stderr)
        sys.exit(1)

    time.sleep(2)
    print(f"[wifi_setup] starting web server on {HOTSPOT_IP}:{WEB_PORT}")
    server = StoppableHTTPServer(("0.0.0.0", WEB_PORT), WifiHandler)

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    if WifiHandler.connected_ok:
        print("[wifi_setup] WiFi configured successfully. Shutting down.")
    else:
        stop_hotspot()
        print("[wifi_setup] shutting down without connecting.")


if __name__ == "__main__":
    main()
