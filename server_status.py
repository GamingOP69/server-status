#!/usr/bin/env python3
"""
Server Status Monitor – Advanced Edition
Features: Email + Discord alerts, Uptime tracking, Beautiful status page, HTTPS support
"""

import os
import json
import socket
import time
import logging
import smtplib
import threading
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ======================== CONFIGURATION ========================
CONFIG_FILE = os.path.abspath('servers.json')
HTML_FILE = os.path.abspath('status.html')
LOG_FILE = os.path.abspath('server_status.log')

CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))
HISTORY_HOURS = 24
MAX_RETRIES = 2
TIMEOUT = 5

# Email
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

# Discord
DISCORD_ENABLED = os.getenv('DISCORD_ENABLED', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# Web Server
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
SSL_ENABLED = os.getenv('SSL_ENABLED', 'false').lower() == 'true'
SSL_CERT = os.getenv('SSL_CERT_FILE', 'cert.pem')
SSL_KEY = os.getenv('SSL_KEY_FILE', 'key.pem')

# ======================== LOGGING ========================
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))
logging.getLogger().addHandler(console)

# ======================== CUSTOM HTTP HANDLER ========================
class CustomHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/status.html')
            self.end_headers()
            return
        if self.path.endswith('/') and self.path != '/':
            self.send_error(404, "Directory listing not allowed")
            return
        super().do_GET()

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, BrokenPipeError):
            pass

def run_web_server():
    server_address = (HOST, PORT)
    if SSL_ENABLED:
        if not os.path.isfile(SSL_CERT) or not os.path.isfile(SSL_KEY):
            logging.error("SSL certificate or key missing. Falling back to HTTP.")
            httpd = ThreadingHTTPServer(server_address, CustomHandler)
            protocol = "http"
        else:
            httpd = ThreadingHTTPServer(server_address, CustomHandler)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(SSL_CERT, SSL_KEY)
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            protocol = "https"
    else:
        httpd = ThreadingHTTPServer(server_address, CustomHandler)
        protocol = "http"

    logging.info(f"🌐 Server running on {protocol}://{HOST}:{PORT}/status.html")
    if HOST == '0.0.0.0':
        logging.info("📡 Accessible from other devices using your LAN/public IP")
    httpd.serve_forever()

# ======================== SERVER MONITOR ========================
class ServerMonitor:
    def __init__(self):
        self.history = {}
        self.last_status = {}
        self.start_time = datetime.now()

    def check_server(self, ip, port):
        for attempt in range(MAX_RETRIES):
            try:
                start = time.perf_counter()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(TIMEOUT)
                    s.connect((ip, port))
                    latency = round((time.perf_counter() - start) * 1000, 2)
                    return True, latency
            except (socket.timeout, ConnectionRefusedError, OSError):
                if attempt == MAX_RETRIES - 1:
                    return False, 0
                time.sleep(1)
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                return False, 0
        return False, 0

    def send_email_alert(self, server, status):
        if not EMAIL_ENABLED or not EMAIL_FROM or not EMAIL_TO:
            return
        name = server['name']
        status_text = "✅ ONLINE" if status else "🔴 OFFLINE"
        color = "#2ecc71" if status else "#e74c3c"
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[ALERT] {name} - {status_text}"
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO

            text = f"""
Server Status Change Alert
--------------------------
Name: {name}
Address: {server['ip']}:{server['port']}
Status: {status_text}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            msg.set_content(text)

            html = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background: #1a1a1a; color: #fff;">
    <h2 style="color: {color};">{status_text}: {name}</h2>
    <div style="background: #2d2d2d; padding: 15px; border-radius: 8px;">
        <p><strong>Address:</strong> {server['ip']}:{server['port']}</p>
        <p><strong>Status:</strong> {status_text}</p>
        <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
"""
            msg.add_alternative(html, subtype="html")

            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
                smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
                smtp.send_message(msg)
            logging.info(f"📧 Email alert sent for {name}")
        except Exception as e:
            logging.error(f"Email failed: {e}")

    def send_discord_alert(self, server, status):
        if not DISCORD_ENABLED or not DISCORD_WEBHOOK_URL:
            return
        import requests
        name = server['name']
        status_text = "✅ ONLINE" if status else "🔴 OFFLINE"
        color = 5763719 if status else 15548997
        embed = {
            "title": f"{status_text}: {name}",
            "description": f"**Address:** `{server['ip']}:{server['port']}`\n**Status:** {status_text}",
            "color": color,
            "fields": [
                {"name": "📡 Latency", "value": f"{self.last_status.get(name, (0,0))[1]}ms" if status else "N/A", "inline": True},
                {"name": "🕒 Last Check", "value": datetime.now().strftime('%H:%M:%S'), "inline": True}
            ],
            "footer": {"text": "Server Monitor • Uptime tracking"},
            "timestamp": datetime.now().isoformat()
        }
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
            if response.status_code == 204:
                logging.info(f"💬 Discord alert sent for {name}")
            else:
                logging.warning(f"Discord returned {response.status_code}")
        except Exception as e:
            logging.error(f"Discord failed: {e}")

    def send_alert(self, server, status):
        self.send_email_alert(server, status)
        self.send_discord_alert(server, status)

    def calculate_uptime(self, name):
        history = self.history.get(name, [])
        if not history:
            return "N/A"
        cutoff = datetime.now() - timedelta(hours=HISTORY_HOURS)
        relevant = [h for h in history if h['timestamp'] > cutoff]
        if not relevant:
            return "N/A"
        online = sum(1 for h in relevant if h['status'])
        return f"{round((online / len(relevant)) * 100, 1)}%"

    def generate_html(self, rows):
        uptime_total = str(datetime.now() - self.start_time).split('.')[0]
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Server Monitor</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <script>
        function refreshData() {{
            fetch(window.location.href)
                .then(response => response.text())
                .then(data => {{
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(data, 'text/html');
                    document.querySelector('tbody').innerHTML = newDoc.querySelector('tbody').innerHTML;
                    document.querySelector('.last-updated').innerHTML = newDoc.querySelector('.last-updated').innerHTML;
                }})
                .catch(err => console.error('Refresh failed:', err));
        }}
        setInterval(refreshData, {CHECK_INTERVAL * 1000});
    </script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #0f0f0f;
            background-image: radial-gradient(circle at 20% 50%, #1a1a2e 0%, #0f0f0f 80%);
            min-height: 100vh;
            color: #fff;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .container {{
            width: 100%;
            max-width: 1200px;
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 2rem;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .header h1 {{
            font-weight: 700;
            font-size: 2.5rem;
            background: linear-gradient(135deg, #f093fb, #f5576c, #4facfe);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .header p {{
            color: #888;
            margin-top: 0.5rem;
        }}
        .card {{
            background: rgba(255,255,255,0.04);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid rgba(255,255,255,0.06);
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 600px;
        }}
        th, td {{
            padding: 1rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        th {{
            font-weight: 600;
            color: #aaa;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.5px;
        }}
        .server-name {{
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        .status-badge.online {{
            background: rgba(46, 204, 113, 0.15);
            color: #2ecc71;
        }}
        .status-badge.offline {{
            background: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 1.5s infinite;
        }}
        .status-dot.online {{ background: #2ecc71; }}
        .status-dot.offline {{ background: #e74c3c; }}
        .latency {{
            font-family: 'Inter', monospace;
            color: #888;
        }}
        .uptime {{
            font-weight: 600;
            color: #4facfe;
        }}
        .last-check {{
            color: #666;
            font-size: 0.85rem;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.85rem;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 1.5rem;
        }}
        @keyframes pulse {{
            0% {{ opacity: 0.6; transform: scale(0.95); }}
            50% {{ opacity: 1; transform: scale(1.1); }}
            100% {{ opacity: 0.6; transform: scale(0.95); }}
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            th, td {{ padding: 0.75rem 0.5rem; font-size: 0.85rem; }}
            .header h1 {{ font-size: 1.8rem; }}
        }}
        @media (max-width: 480px) {{
            table {{ min-width: 400px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Server Monitor</h1>
            <p>Real‑time status • Uptime tracking • Instant alerts</p>
        </div>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>Server</th>
                        <th>Status</th>
                        <th>Latency</th>
                        <th>Address</th>
                        <th>Uptime (24h)</th>
                        <th>Last Check</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        <div class="footer">
            <p class="last-updated">🕒 Last updated: {now_str} | ⏱️ Monitor uptime: {uptime_total}</p>
        </div>
    </div>
</body>
</html>"""

        temp = HTML_FILE + ".tmp"
        with open(temp, 'w', encoding='utf-8') as f:
            f.write(html)
        os.replace(temp, HTML_FILE)

    def generate_row(self, server, status, latency):
        uptime = self.calculate_uptime(server['name'])
        status_class = "online" if status else "offline"
        status_text = "Online" if status else "Offline"
        return f"""
        <tr>
            <td><span class="server-name">{server['name']}</span></td>
            <td>
                <span class="status-badge {status_class}">
                    <span class="status-dot {status_class}"></span>
                    {status_text}
                </span>
            </td>
            <td class="latency">{latency}ms</td>
            <td><code>{server['ip']}:{server['port']}</code></td>
            <td class="uptime">{uptime}</td>
            <td class="last-check">{datetime.now().strftime('%H:%M:%S')}</td>
        </tr>
        """

    def update_history(self, name, status):
        now = datetime.now()
        self.history.setdefault(name, []).append({"timestamp": now, "status": status})
        cutoff = now - timedelta(hours=HISTORY_HOURS)
        self.history[name] = [h for h in self.history[name] if h['timestamp'] > cutoff]

    def load_servers(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            servers = data.get('servers', [])
            valid = [s for s in servers if all(k in s for k in ['name', 'ip', 'port'])]
            return valid
        except Exception as e:
            logging.critical(f"Config load failed: {e}")
            return []

    def run(self):
        logging.info("🚀 Starting server monitor")
        servers = self.load_servers()
        if not servers:
            logging.error("No valid servers found. Exiting.")
            return
        # Initial check
        for s in servers:
            status, _ = self.check_server(s['ip'], s['port'])
            self.last_status[s['name']] = status
            self.update_history(s['name'], status)
            if not status:
                self.send_alert(s, False)

        while True:
            try:
                servers = self.load_servers()
                rows = []
                for s in servers:
                    name = s['name']
                    prev = self.last_status.get(name)
                    status, latency = self.check_server(s['ip'], s['port'])
                    self.update_history(name, status)
                    if prev is not None and status != prev:
                        self.send_alert(s, status)
                    self.last_status[name] = status
                    rows.append(self.generate_row(s, status, latency))
                self.generate_html(rows)
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logging.info("Stopped by user")
                break
            except Exception as e:
                logging.error(f"Main loop error: {e}")
                time.sleep(60)

# ======================== MAIN ========================
if __name__ == "__main__":
    # Test alerts
    if EMAIL_ENABLED and EMAIL_FROM and EMAIL_TO:
        try:
            monitor = ServerMonitor()
            monitor.send_email_alert({"name": "Test", "ip": "test", "port": 0}, False)
            logging.info("📧 Test email sent")
        except Exception as e:
            logging.error(f"Email test failed: {e}")

    if DISCORD_ENABLED and DISCORD_WEBHOOK_URL:
        try:
            monitor = ServerMonitor()
            monitor.send_discord_alert({"name": "Test", "ip": "test", "port": 0}, True)
            logging.info("💬 Test Discord sent")
        except Exception as e:
            logging.error(f"Discord test failed: {e}")

    monitor = ServerMonitor()
    t = threading.Thread(target=monitor.run)
    t.daemon = True
    t.start()
    run_web_server()