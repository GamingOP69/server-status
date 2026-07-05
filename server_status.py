#!/usr/bin/env python3
"""
Server Status Monitor with Email and Discord Alerts
"""

import os
import json
import socket
import time
import logging
import smtplib
import threading
from datetime import datetime, timedelta
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will rely on system env vars

# Configuration
CONFIG_FILE = os.path.abspath('servers.json')
HTML_FILE = os.path.abspath('status.html')
LOG_FILE = os.path.abspath('server_status.log')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
HISTORY_HOURS = 24
MAX_RETRIES = 2
TIMEOUT = 5  # seconds per connection attempt

# Email Configuration
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'true').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
EMAIL_FROM = os.getenv('EMAIL_FROM', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

# Discord Webhook Configuration
DISCORD_ENABLED = os.getenv('DISCORD_ENABLED', 'false').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Also log to console for immediate feedback
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))
logging.getLogger().addHandler(console)

# ----------------------------------------------------------------------
# Web Server (serves the generated HTML file)
# ----------------------------------------------------------------------
class CustomHandler(SimpleHTTPRequestHandler):
    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, BrokenPipeError):
            pass

def run_web_server(port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, CustomHandler)
    logging.info(f"Web server running on http://localhost:{port}/status.html")
    httpd.serve_forever()

# ----------------------------------------------------------------------
# Server Monitor
# ----------------------------------------------------------------------
class ServerMonitor:
    def __init__(self):
        self.server_history = {}  # {name: [{'timestamp': datetime, 'status': bool}]}
        self.last_status = {}      # {name: bool}
        self.start_time = datetime.now()
        self.alert_cooldown = {}   # {name: datetime} to prevent spam

    def check_server(self, ip, port):
        """Check server connectivity and measure latency."""
        for attempt in range(MAX_RETRIES):
            try:
                start = time.perf_counter()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(TIMEOUT)
                    s.connect((ip, port))
                    latency = round((time.perf_counter() - start) * 1000, 2)
                    return True, latency
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                if attempt == MAX_RETRIES - 1:
                    logging.warning(f"Server {ip}:{port} unreachable: {e}")
                    return False, 0
                time.sleep(1)
            except Exception as e:
                logging.error(f"Unexpected error checking {ip}:{port}: {e}")
                return False, 0
        return False, 0

    def send_email_alert(self, server, status):
        """Send email alert with HTML and plain text."""
        if not EMAIL_ENABLED or not EMAIL_FROM or not EMAIL_TO:
            return

        server_name = server['name']
        status_text = "ONLINE" if status else "OFFLINE"
        color = "#2ecc71" if status else "#e74c3c"

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[ALERT] {server_name} - {status_text}"
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO

            # Plain text
            text = f"""
Server Status Change Alert
--------------------------
Name: {server_name}
Address: {server['ip']}:{server['port']}
Status: {status_text}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            msg.set_content(text)

            # HTML
            html = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">
        {status_text}: {server_name}
    </h2>
    <div style="margin-top: 20px;">
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
            logging.info(f"Email alert sent for {server_name} ({status_text})")
        except smtplib.SMTPAuthenticationError:
            logging.error("SMTP authentication failed - check credentials")
        except Exception as e:
            logging.error(f"Email sending failed: {e}")

    def send_discord_alert(self, server, status):
        """Send alert to Discord webhook."""
        if not DISCORD_ENABLED or not DISCORD_WEBHOOK_URL:
            return

        import requests  # lazy import to avoid requirement if not used

        server_name = server['name']
        status_text = "✅ ONLINE" if status else "🔴 OFFLINE"
        color = 5763719 if status else 15548997  # green / red

        payload = {
            "embeds": [{
                "title": f"{status_text}: {server_name}",
                "description": f"**Address:** `{server['ip']}:{server['port']}`\n**Status:** {status_text}\n**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "color": color,
                "footer": {"text": "Server Monitor"}
            }]
        }

        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 204:
                logging.info(f"Discord alert sent for {server_name}")
            else:
                logging.warning(f"Discord webhook returned {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"Discord webhook failed: {e}")

    def send_alert(self, server, status):
        """Send alerts via email and Discord."""
        self.send_email_alert(server, status)
        self.send_discord_alert(server, status)

    def generate_html(self, rows):
        """Generate the HTML status page."""
        uptime_str = str(datetime.now() - self.start_time).split('.')[0]
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Server Monitor</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500&display=swap" rel="stylesheet">
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
        :root {{
            --online: #2ecc71;
            --offline: #e74c3c;
            --background: #1a1a1a;
            --card-bg: #2d2d2d;
            --text: #ffffff;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Roboto', sans-serif;
            background-color: var(--background);
            color: var(--text);
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 2rem auto;
            padding: 2rem;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            animation: fadeIn 1s ease-in;
        }}
        .status-card {{
            background: var(--card-bg);
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .status-card:hover {{ transform: translateY(-5px); }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}
        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #3d3d3d;
        }}
        th {{
            background-color: #333333;
            font-weight: 500;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 0.5rem;
            animation: pulse 1.5s infinite;
        }}
        .online {{ background-color: var(--online); }}
        .offline {{ background-color: var(--offline); }}
        .latency {{ font-size: 0.9rem; color: #95a5a6; }}
        .last-updated {{
            text-align: center;
            color: #7f8c8d;
            margin-top: 2rem;
            font-size: 0.9rem;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.7; }}
            70% {{ transform: scale(1.1); opacity: 0.4; }}
            100% {{ transform: scale(0.95); opacity: 0.7; }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            th, td {{ padding: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Game Server Monitor</h1>
        </div>
        <div class="status-card">
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
        <p class="last-updated">
            Last updated: {now_str} | Uptime: {uptime_str}
        </p>
    </div>
</body>
</html>"""

        temp_file = HTML_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(html)
        os.replace(temp_file, HTML_FILE)

    def calculate_uptime(self, server_name):
        """Calculate uptime percentage over HISTORY_HOURS."""
        history = self.server_history.get(server_name, [])
        if not history:
            return "N/A"
        cutoff = datetime.now() - timedelta(hours=HISTORY_HOURS)
        relevant = [h for h in history if h['timestamp'] > cutoff]
        if not relevant:
            return "N/A"
        online_count = sum(1 for h in relevant if h['status'])
        return f"{round((online_count / len(relevant)) * 100, 1)}%"

    def generate_row(self, server, status, latency):
        """Generate a table row with uptime."""
        uptime = self.calculate_uptime(server['name'])
        return f"""
        <tr>
            <td>{server['name']}</td>
            <td>
                <span class="status-indicator {'online' if status else 'offline'}"></span>
                {'Online' if status else 'Offline'}
            </td>
            <td>{latency}ms</td>
            <td>{server['ip']}:{server['port']}</td>
            <td>{uptime}</td>
            <td>{datetime.now().strftime('%H:%M:%S')}</td>
        </tr>
        """

    def update_history(self, server_name, status):
        """Store status in history and prune old entries."""
        now = datetime.now()
        self.server_history.setdefault(server_name, []).append({
            "timestamp": now,
            "status": status
        })
        cutoff = now - timedelta(hours=HISTORY_HOURS)
        self.server_history[server_name] = [
            h for h in self.server_history[server_name]
            if h["timestamp"] > cutoff
        ]

    def load_servers(self):
        """Load server list from JSON file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            servers = data.get('servers', [])
            # Validate each server entry
            valid = []
            for s in servers:
                if all(k in s for k in ['name', 'ip', 'port']):
                    valid.append(s)
                else:
                    logging.warning(f"Skipping invalid server entry: {s}")
            return valid
        except Exception as e:
            logging.critical(f"Failed to load servers.json: {e}")
            return []

    def run(self):
        """Main monitoring loop."""
        logging.info("Starting server monitor")
        servers = self.load_servers()
        if not servers:
            logging.error("No valid servers found. Exiting.")
            return

        # Initial check to set baseline
        for server in servers:
            status, _ = self.check_server(server["ip"], server["port"])
            self.last_status[server['name']] = status
            self.update_history(server['name'], status)
            if not status:
                self.send_alert(server, False)

        while True:
            try:
                servers = self.load_servers()
                rows = []
                for server in servers:
                    name = server['name']
                    prev = self.last_status.get(name)
                    status, latency = self.check_server(server["ip"], server["port"])

                    self.update_history(name, status)

                    if prev is not None and status != prev:
                        self.send_alert(server, status)

                    self.last_status[name] = status
                    rows.append(self.generate_row(server, status, latency))

                self.generate_html(rows)
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Critical error in main loop: {e}")
                time.sleep(60)

# ----------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Quick test of email/Discord configuration
    if EMAIL_ENABLED and EMAIL_FROM and EMAIL_TO:
        try:
            test_server = {"name": "Test Alert", "ip": "test", "port": 0}
            monitor = ServerMonitor()
            monitor.send_email_alert(test_server, False)
            logging.info("Test email sent (check your inbox)")
        except Exception as e:
            logging.error(f"Test email failed: {e}")

    if DISCORD_ENABLED and DISCORD_WEBHOOK_URL:
        try:
            import requests
            test_server = {"name": "Test Alert", "ip": "test", "port": 0}
            monitor = ServerMonitor()
            monitor.send_discord_alert(test_server, True)
            logging.info("Test Discord message sent")
        except Exception as e:
            logging.error(f"Test Discord failed: {e}")

    # Start monitor in background thread
    monitor = ServerMonitor()
    monitor_thread = threading.Thread(target=monitor.run)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Run web server (blocks main thread)
    run_web_server()