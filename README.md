
# SmartSocialLinkBot

![SmartSocialLinkBot Logo](assets/logo.webp)

[![Support me on Ko-fi](https://storage.ko-fi.com/cdn/kofi2.png?v=3)](https://ko-fi.com/S6S119KZVL)

**SmartSocialLinkBot** is a Telegram bot designed to manage social media links (Instagram, Twitter/X, TikTok) within authorized groups. The bot can fix malformed links, replace specific domains, and ensure links are shared in the desired format. 

---

## Key Features

### Group Management
- **White-listed Groups:** The bot operates only in groups explicitly authorized by the admin.
- **Automatic Group Registration:** If the admin adds the bot to a group, it automatically registers the group in the database.
- **Automatic Expulsion:** If the bot is added to an unauthorized group, it removes itself automatically.
- **Interactive Group Removal:** Groups can now be removed interactively via the menu or by providing the group ID using the `/remove_group` command.

### Link Processing
- **Malformed Link Correction:** The bot normalizes malformed links. For example:
  - `https://fixupfixupx.com` → `https://fixupx.com`
  - `https://instagram.com` → `https://ddinstagram.com`
- **Domain Replacement:** The bot replaces specific domains based on configured rules:
  - `instagram.com` → `ddinstagram.com`
  - `twitter.com` or `x.com` → `fixupx.com`
  - `tiktok.com` → `vxtiktok.com`

### Permissions Handling
- **Message Editing or Deletion:** If the bot has permission to delete messages, it deletes the original and sends a new message with the corrected link.
- **Alternative Replies:** If the bot cannot delete messages, it replies to the original message with the corrected link.

### Simplified Group ID Handling
- You no longer need to prepend a negative symbol to group IDs when adding or removing groups. The bot automatically handles it.

---

## Available Commands

### Admin Commands
These commands can only be executed by the registered admin of the bot:

- `/menu` - Displays an interactive menu with buttons to manage the bot.
- `/list_groups` - Lists all groups where the bot is authorized.
- `/add_group <GROUP_ID>` - Manually adds a group to the authorized list.
- `/remove_group <GROUP_ID>` - Removes a group from the authorized list and expels the bot from it. Groups can also be removed interactively via the menu.
- `/list_attempts` - Lists all unauthorized attempts to add the bot to groups.
- `/help` - Displays a list of available commands.

---

## Installation

### Requirements
- Python 3.10 or higher.
- MongoDB to store group data.
- Docker and Docker Compose (optional for deployment).

### Setup
1. Clone this repository:
   ```bash
   git clone <repository_url>
   cd SmartSocialLinkBot
   ```

2. Create a `.env` file inside the `config` directory with the following content:
   ```env
   BOT_TOKEN=<your_bot_token>
   ADMIN_ID=<your_admin_id>
   MONGO_URI=<your_mongodb_uri>
   DB_NAME=telegram_bot
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

---

## Using Docker

1. Build the Docker image:
   ```bash
   docker build -t smartsociallinkbot .
   ```

2. Configure `docker-compose.yml` to deploy the bot and MongoDB:
   ```yaml
   services:
     bot:
       build: .
       container_name: smartsociallinkbot
       env_file:
         - ./config/.env
       volumes:
         - ./config:/app/config:ro
       restart: always
     mongodb:
       image: mongo:6.0
       container_name: telegram_bot_mongodb
       restart: always
       ports:
         - "27017:27017"
   ```

3. Start the containers:
   ```bash
   docker-compose up -d
   ```

---

## Project Architecture

```
SmartSocialLinkBot/
├── main.py                # Main file to initialize the bot
├── commands.py            # Bot commands
├── handlers.py            # Message processing logic
├── db.py                  # Database connection and handling
├── config/
│   └── .env               # Bot configuration file
├── requirements.txt       # Project dependencies
├── Dockerfile             # Docker configuration
└── docker-compose.yml     # Docker Compose configuration
```

---

## Future Features
- Integration with additional social networks.
- Analytics to track bot usage and performance.

---

## Contributions
Contributions are welcome! If you have ideas or encounter issues, feel free to:
- Open an issue to report a bug or suggest a feature.
- Submit a pull request with your contributions.

---

## License
This project is licensed under the [MIT License](LICENSE).
