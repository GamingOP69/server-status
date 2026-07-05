# Server Status Monitor

Monitor the health and availability of game servers and websites with real-time monitoring, email notifications, and Discord alerts.

## Features

- **Real-time status checks** – Monitors servers every 60 seconds (configurable).
- **Email alerts** – Sends notifications when a server goes online or offline.
- **Discord webhook support** – Posts status updates to any Discord channel.
- **Uptime tracking** – Displays the 24-hour uptime percentage for each server.
- **Live status page** – Automatically refreshes with server status, latency, and the last check time.
- **Easy configuration** – Configure servers and credentials using `servers.json` and `.env`.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/GamingOP69/server-status.git
   cd server-status
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv

   # Linux / macOS
   source venv/bin/activate

   # Windows
   venv\Scripts\activate
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file and configure it:

   ```bash
   cp .env.example .env
   ```

   Then edit the `.env` file and add your email and Discord credentials.

## Usage

1. Edit `servers.json` and add the servers or websites you want to monitor.
2. Start the monitor:

   ```bash
   python server_status.py
   ```

3. Open the live status page in your browser:

   ```
   http://localhost:8000/status.html
   ```

## Configuration

### `servers.json`

Configure the servers you want to monitor.

Example fields:

- `name`
- `ip`
- `port`
- `type` *(optional)*

### `.env`

Configure application settings:

**Email**

- `EMAIL_ENABLED`
- `EMAIL_FROM`
- `EMAIL_TO`
- `EMAIL_PASSWORD`

**Discord**

- `DISCORD_ENABLED`
- `DISCORD_WEBHOOK_URL`

**Monitoring**

- `CHECK_INTERVAL` – Monitoring interval in seconds.

## License

This project is licensed under the MIT License. See the [`LICENSE`](LICENSE) file for more information.
