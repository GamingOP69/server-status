# Server Status Monitor

This project monitors the status of various servers and websites, sending email alerts when their status changes.

## Features

- Monitor multiple servers and websites
- Send email alerts on status changes
- Generate a status page with history

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/GamingOP69/server-status.git
    cd server-status
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file with your email configuration:
    ```plaintext
    EMAIL_FROM=your_email@gmail.com
    EMAIL_TO=recipient_email@gmail.com
    EMAIL_PASSWORD=your_email_password
    ```

## Usage

1. Update the `servers.json` file with the servers and websites you want to monitor.

2. Run the server monitor:
    ```sh
    python server_status.py
    ```

3. Access the status page at `http://localhost:8000/status.html`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

