# TTM
Auto trade and manage stocks/coins platform
<p align="center">
</p>
  <p align="center">
    <a href="https://github.com/anuraghazra/github-readme-stats/actions">
      <img alt="Tests Passing" src="https://github.com/anuraghazra/github-readme-stats/workflows/Test/badge.svg" />
    </a>
    <a href="https://codecov.io/gh/anuraghazra/github-readme-stats">
      <img alt="Tests Coverage" src="https://codecov.io/gh/anuraghazra/github-readme-stats/branch/master/graph/badge.svg" />
    </a>
    <br />
    <a href="https://github.com/anuraghazra/github-readme-stats/issues">
      <img alt="Issues" src="https://img.shields.io/github/issues/anuraghazra/github-readme-stats?color=0088ff" />
    </a>
    <a href="https://github.com/anuraghazra/github-readme-stats/pulls">
      <img alt="GitHub pull requests" src="https://img.shields.io/github/issues-pr/anuraghazra/github-readme-stats?color=0088ff" />
    </a>
    <br />
    <br />

  </p>


## Requirements
- python 12.0
- poetry 1.6.1
- fastapi 0.104.1


## Installation
### 1. Download repo
```
git clone https://github.com/CasselKim/TTM.git`
```

### 2. Download poetry
https://python-poetry.org/docs/#installing-with-the-official-installer

### 3. Create venv
```
poetry install
```

### 4. Configuration
Create `.env` file and set the following environment variables:
```bash
# Upbit API Keys
UPBIT_ACCESS_KEY=your_upbit_access_key_here
UPBIT_SECRET_KEY=your_upbit_secret_key_here

# Discord Bot Settings (optional)
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_discord_channel_id_here

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

#### Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and go to the Bot section
3. Create a bot and copy the bot token
4. Enable necessary Intents (MESSAGE CONTENT INTENT is required)
5. Invite the bot to your server with appropriate permissions (Send Messages, Embed Links)
6. Get the channel ID where you want the bot to send messages (Enable Developer Mode in Discord)
7. Set the `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` in your `.env` file

### 5. Execute docker
```
docker build -f docker/Dockerfile . -t ttm-image
docker compose -f docker/docker-compose-local.yml -p ttm up -d
```
### 5. Check the access
http://0.0.0.0/docs
![image](docs/local_test.png)

## Deployment - Github Action
1. PR open
2. Test by github action
3. Auto-merge when test pass
4. Build as image and push to Docker hub
5. Run the image on the AWS EC2 through github action

## License
This project is licensed under the terms of the MIT license.

## Features

### Trading
- **Upbit Integration**: Support for limit/market buy/sell orders
- **Account Management**: Check balances and account information
- **Market Data**: Real-time ticker information

### Notifications
- **Discord Bot Notifications**: Get real-time alerts via Discord Bot for:
  - Trade executions (buy/sell)
  - Error notifications
  - System status updates
- **Rich Embed Messages**: Beautiful formatted messages with colors and fields
- **Bot Commands**: (Future feature) Execute trades and check status via Discord commands

## Testing Discord Bot
Run the Discord bot test script:
```bash
python scripts/test_discord_bot.py
```
