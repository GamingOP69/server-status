import socket
import json
import time
import os
import logging
import smtplib
import threading
from datetime import datetime, timedelta
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

# Configuration
CONFIG_FILE = os.path.abspath('servers.json')
HTML_FILE = os.path.abspath('status.html')
LOG_FILE = os.path.abspath('server_status.log')
CHECK_INTERVAL = 60  # Seconds between checks
HISTORY_HOURS = 24  # Show 24-hour history
MAX_RETRIES = 2  # Connection attempts
TIMEOUT = 5  # Seconds per connection attempt

# Email Configuration
EMAIL_ENABLED = True
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_FROM = os.getenv("EMAIL_FROM", "default_email@gmail.com")
EMAIL_TO = os.getenv("EMAIL_TO", "default_email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "default_password")

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class CustomHandler(SimpleHTTPRequestHandler):
    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionAbortedError, BrokenPipeError):
            pass

def run_web_server(port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, CustomHandler)
    print(f"Serving on port {port}")
    httpd.serve_forever()

class ServerMonitor:
    def __init__(self):
        self.server_history = {}
        self.last_status = {}
        self.start_time = datetime.now()
        self.alert_cooldown = {}

    def check_server(self, ip, port):
        """Check server with retries and latency measurement"""
        for attempt in range(MAX_RETRIES):
            try:
                start = time.perf_counter()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(TIMEOUT)
                    s.connect((ip, port))
                    latency = round((time.perf_counter() - start) * 1000, 2)
                    return True, latency
            except (socket.timeout, ConnectionRefusedError):
                if attempt == MAX_RETRIES - 1:
                    return False, 0
                time.sleep(1)
            except Exception as e:
                logging.error(f"Connection error {ip}:{port} - {str(e)}")
                return False, 0
        return False, 0

    def send_alert(self, server, new_status):
        """Send email alert with HTML and plain text versions"""
        if not EMAIL_ENABLED:
            return

        server_name = server['name']
        status_text = "ONLINE" if new_status else "OFFLINE"
        color = "#2ecc71" if new_status else "#e74c3c"
        
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[ALERT] {server_name} - {status_text}"
            msg["From"] = EMAIL_FROM
            msg["To"] = EMAIL_TO

            # Plain text version
            text_content = fr"""
            Server Status Change Alert
            --------------------------
            Name: {server_name}
            Address: {server['ip']}:{server['port']}
            Status: {status_text}
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            msg.set_content(text_content)



            # HTML version
            html_content = fr"""
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
            msg.add_alternative(html_content, subtype="html")

            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
                smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
                smtp.send_message(msg)
                logging.info(f"Sent alert for {server_name} ({status_text})")

        except smtplib.SMTPAuthenticationError:
            logging.error("SMTP Authentication Failed - Check credentials")
        except smtplib.SMTPException as e:
            logging.error(f"SMTP error occurred: {e}")
        except Exception as e:
            logging.error(f"Email failed: {str(e)}")

    def generate_html(self, servers):
        """Generate status page with history chart"""
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
                }});
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

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

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
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}

        .status-card:hover {{
            transform: translateY(-5px);
        }}

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

        .latency {{
            font-size: 0.9rem;
            color: #95a5a6;
        }}

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
                        <th>Last Check</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(servers)}
                </tbody>
            </table>
        </div>
        
        <p class="last-updated">
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            Uptime: {str(datetime.now() - self.start_time).split('.')[0]}
        </p>
    </div>
</body>
</html>"""
        
        temp_file = HTML_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(html)
        os.replace(temp_file, HTML_FILE)

    def run(self):
        """Main monitoring loop"""
        logging.info("Starting server monitor")
        
        servers = self.load_servers()
        for server in servers:
            server_name = server['name']
            status, _ = self.check_server(server["ip"], server["port"])
            self.last_status[server_name] = status
            if not status:
                self.send_alert(server, False)

        while True:
            try:
                servers = self.load_servers()
                server_rows = []
                
                for server in servers:
                    server_name = server['name']
                    previous_status = self.last_status.get(server_name)
                    status, latency = self.check_server(server["ip"], server["port"])
                    
                    self.update_history(server_name, status)
                    
                    if previous_status is not None and status != previous_status:
                        self.send_alert(server, status)
                    
                    self.last_status[server_name] = status
                    server_rows.append(self.generate_row(server, status, latency))
                
                self.generate_html(server_rows)
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logging.info("Monitoring stopped by user")
                break
            except Exception as e:
                logging.error(f"Critical error: {str(e)}")
                time.sleep(60)

    def generate_row(self, server, status, latency):
        return f"""
        <tr>
            <td>{server['name']}</td>
            <td>
                <span class="status-indicator {'online' if status else 'offline'}"></span>
                {'Online' if status else 'Offline'}
            </td>
            <td>{latency}ms</td>
            <td>{server['ip']}:{server['port']}</td>
            <td>{datetime.now().strftime('%H:%M:%S')}</td>
        </tr>
        """

    def update_history(self, server_name, status):
        now = datetime.now()
        self.server_history.setdefault(server_name, []).append({
            "timestamp": now,
            "status": status
        })
        cutoff = now - timedelta(hours=HISTORY_HOURS)
        self.server_history[server_name] = [
            entry for entry in self.server_history[server_name]
            if entry["timestamp"] > cutoff
        ]

    def load_servers(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                servers = json.load(f).get('servers', [])
                return [s for s in servers if all(k in s for k in ['name', 'ip', 'port'])]
        except Exception as e:
            logging.critical(f"Config error: {str(e)}")
            return []

if __name__ == "__main__":
    # Start monitoring thread
    monitor = ServerMonitor()
    
    if EMAIL_ENABLED:
        try:
            monitor.send_alert({
                "name": "Test Mesaage for checking email",
                "ip": "",
                "port": None
            }, False)
        except Exception as e:
            print(f"Email test failed: {e}")

    monitor_thread = threading.Thread(target=monitor.run)
    monitor_thread.daemon = True
    monitor_thread.start()

    # Start web server in main thread
    run_web_server()