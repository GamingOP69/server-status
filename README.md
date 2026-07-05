# Server Status Monitor

Monitor the health of game servers and websites with real‑time checks, email alerts, and Discord notifications.

## Features

- **Real‑time status checks** – pings servers every 60 seconds (configurable).
- **Email alerts** – sends notifications when a server goes online/offline.
- **Discord webhook** – posts alerts to any Discord channel.
- **Uptime percentage** – shows 24‑hour uptime for each server.
- **Live status page** – auto‑refreshes with latency, last check time, and uptime.
- **Easy configuration** – all servers in `servers.json`, credentials in `.env`.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/GamingOP69/server-status.git
   cd server-status
```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate      # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment template and fill in your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your email and Discord settings
   ```

Usage

1. Edit servers.json to add the servers you want to monitor (name, IP, port).
2. Run the monitor:
   ```bash
   python server_status.py
   ```
3. Open the status page at http://localhost:8000/status.html.

Configuration

Servers (servers.json)

Each entry must contain:

· name – display name
· ip – hostname or IP address
· port – port number

Example:

```json
{
    "servers": [
        { "name": "Hypixel", "ip": "mc.hypixel.net", "port": 25565 }
    ]
}
```

Environment Variables (.env)

Variable Description
EMAIL_ENABLED true/false
EMAIL_FROM Sender email address
EMAIL_TO Recipient email address
EMAIL_PASSWORD App password for SMTP (Gmail)
DISCORD_ENABLED true/false
DISCORD_WEBHOOK_URL Discord webhook URL
CHECK_INTERVAL Seconds between checks (default: 60)

Example .env:

```ini
EMAIL_ENABLED=true
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
EMAIL_PASSWORD=your_app_password
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
CHECK_INTERVAL=60
```

⚠️ Gmail users: Use an App Password – not your normal password.

License

This project is licensed under the MIT License – see the LICENSE file for details.
