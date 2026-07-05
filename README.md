# Server Status Monitor

Monitor the health of game servers and websites with email and Discord alerts.

## Features

- **Real‑time status checks** – pings servers every 60 seconds (configurable).
- **Email alerts** – sends notifications when a server goes online/offline.
- **Discord webhook** – posts alerts to any Discord channel.
- **Uptime percentage** – shows 24‑hour uptime for each server.
- **Live status page** – auto‑refreshes with latency and last check time.
- **Easy configuration** – all servers and credentials in JSON + `.env`.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GamingOP69/server-status.git
   cd server-status
```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy .env.example to .env and fill in your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your email and Discord settings
   ```

Usage

1. Edit servers.json to add the servers you want to monitor.
2. Run the monitor:
   ```bash
   python server_status.py
   ```
3. Open the status page at http://localhost:8000/status.html.

Configuration

· Servers: servers.json – list of objects with name, ip, port, and optional type.
· Email: .env – set EMAIL_ENABLED, EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD.
· Discord: .env – set DISCORD_ENABLED and DISCORD_WEBHOOK_URL.
· Interval: .env – CHECK_INTERVAL (seconds).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
