# Discord Scraper Dashboard

A comprehensive Discord scraping solution with both CLI and web dashboard interfaces.

## Components

### 1. CLI Script (`discord_export.py`)
A standalone Python script that automatically downloads and uses [DiscordChatExporter](https://github.com/Tyrrrz/DiscordChatExporter) to export Discord chat logs.

### 2. Web Dashboard
A modern web interface for managing Discord exports with incremental scraping capabilities.

## Features

- **Auto-setup**: Automatically downloads DiscordChatExporter on first run
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Multiple formats**: Export to HTML (default), JSON, CSV, or TXT
- **Configuration support**: Save settings for repeated exports
- **Progress feedback**: See export progress in real-time
- **Media downloads**: Optionally include attachments and media
- **Date filtering**: Export messages from specific time periods

## Requirements

- Python 3.7 or higher
- A Discord bot token (see setup instructions below)
- Internet connection (for first-time DCE download)

## Installation

1. Clone or download this repository:
```bash
git clone <repository-url>
cd discord_scrapper
```

2. No dependencies to install! The script uses only Python standard library.

## Setting Up a Discord Bot

Before using this script, you need to create a Discord bot and get its token:

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot"
5. Under "Token", click "Copy" to get your bot token
6. **Important**: Keep this token secret!

### Adding Your Bot to a Server

1. In the Developer Portal, go to "OAuth2" > "URL Generator"
2. Select these scopes:
   - `bot`
3. Select these bot permissions:
   - `Read Messages/View Channels`
   - `Read Message History`
4. Copy the generated URL and open it in your browser
5. Select the server and click "Authorize"

## Usage

### Basic Export

Export a channel to HTML (default):
```bash
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN
```

### Export Formats

Export to different formats:
```bash
# JSON format
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN -f json

# CSV format
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN -f csv

# Plain text
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN -f txt
```

### Advanced Options

```bash
# Specify output directory
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN -o ./backups

# Filter by date
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN --after 2024-01-01 --before 2024-12-31

# Don't download media attachments (faster export)
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN --no-media

# Use configuration file
python discord_export.py -c CHANNEL_ID --config myconfig.json
```

### Configuration File

Save your settings for repeated use:

```bash
# Save current settings to config.json
python discord_export.py -c CHANNEL_ID -t YOUR_BOT_TOKEN --save-config
```

Example `config.json`:
```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "default_format": "html",
  "output_directory": "./exports",
  "include_attachments": true
}
```

Once saved, you can export without providing the token:
```bash
python discord_export.py -c CHANNEL_ID --config config.json
```

## Getting Channel IDs

1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Developer Mode
2. Right-click on any channel
3. Click "Copy Channel ID"

## Output

Exports are saved in the `exports` directory by default with the filename format:
```
CHANNELID_YYYYMMDD_HHMMSS.format
```

Example: `123456789012345678_20240115_143022.html`

## File Structure

After running the script:
```
discord_scrapper/
├── discord_export.py      # Main script
├── config.json           # Configuration (created with --save-config)
├── dce/                  # DiscordChatExporter (auto-downloaded)
│   └── DiscordChatExporter.Cli[.exe]
└── exports/              # Exported chat logs
    └── [channel_id]_[timestamp].[format]
```

## Troubleshooting

### "Bot token is invalid or bot doesn't have access"
- Verify your bot token is correct
- Ensure the bot is added to the server
- Check that the bot has "Read Message History" permission

### "Channel not found"
- Double-check the channel ID
- Ensure the bot can see the channel (check channel permissions)

### Download fails
- Check your internet connection
- If auto-download fails, manually download DiscordChatExporter from:
  https://github.com/Tyrrrz/DiscordChatExporter/releases
- Extract it to the `dce` folder in the script directory

### Permission errors on macOS/Linux
- The script automatically makes DCE executable
- If issues persist, manually run: `chmod +x dce/DiscordChatExporter.Cli`

## Security Notes

- **Never share your bot token publicly**
- The config file stores tokens in plain text - keep it secure
- Consider using environment variables for tokens in production
- Bot tokens are safer than user tokens (which violate Discord ToS)

## Web Dashboard Quick Start

### Prerequisites
- Docker and Docker Compose
- Discord Application with OAuth2 configured
- Discord Bot Token

### Setup
1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your Discord credentials
3. Run the start script:
   ```bash
   ./start.sh
   ```

4. Access the dashboard at http://localhost:3000

### Dashboard Features
- **Server Browser**: Visual interface to browse your Discord servers
- **Channel Selection**: Select multiple channels for batch exports  
- **Incremental Scraping**: Only export new messages since last sync
- **Job Management**: Monitor export progress in real-time
- **Export History**: Track all your scraping operations

## Architecture

```
Frontend (React + TypeScript + Material-UI)
    ↓
Backend API (FastAPI + PostgreSQL)
    ↓
Job Queue (Redis + RQ)
    ↓
Worker Process → discord_export.py → DiscordChatExporter
```

## License

This project is provided as-is for educational and backup purposes. Please respect Discord's Terms of Service and rate limits when using this tool.

DiscordChatExporter is created by [Tyrrrz](https://github.com/Tyrrrz) and is licensed under the MIT License.