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

# Discord Admin User IDs for trading commands (comma-separated)
# Enable Developer Mode in Discord and right-click user to copy ID
DISCORD_ADMIN_USER_IDS=123456789012345678,987654321098765432

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

#### Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and go to the Bot section
3. Create a bot and copy the bot token
4. Enable necessary Intents (MESSAGE CONTENT INTENT is required)
5. Invite the bot to your server with appropriate permissions (Send Messages, Embed Links, Add Reactions)
6. Get the channel ID where you want the bot to send messages (Enable Developer Mode in Discord)
7. Get your Discord User ID for admin privileges (Enable Developer Mode and right-click your profile)
8. Set the `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_ID`, and `DISCORD_ADMIN_USER_IDS` in your `.env` file

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
- **Order Management**: View and cancel orders

### Discord Bot Commands
- **Basic Commands** (All users):
  - `!잔고` or `!balance` - Check account balance
  - `!시세 [MARKET]` or `!price [MARKET]` - Get ticker information
  - `!도움말` or `!명령어` - Show help message

- **Trading Commands** (Admin only):
  - `!매수 [MARKET] [AMOUNT]` - Market buy order
  - `!매수 [MARKET] [VOLUME] [PRICE]` - Limit buy order
  - `!매도 [MARKET] [VOLUME]` - Market sell order
  - `!매도 [MARKET] [VOLUME] [PRICE]` - Limit sell order
  - `!주문조회 [UUID]` - Get order information
  - `!주문취소 [UUID]` - Cancel order

- **Security Features**:
  - Admin-only access for trading commands
  - Interactive confirmation for all trades
  - Maximum trade amount limits
  - 30-second timeout for confirmations

### Notifications
- **Discord Bot Notifications**: Get real-time alerts via Discord Bot for:
  - Trade executions (buy/sell)
  - Order cancellations
  - Error notifications
  - System status updates
- **Rich Embed Messages**: Beautiful formatted messages with colors and fields

## Testing Discord Bot
Run the Discord bot test script:
```bash
python scripts/test_discord_bot.py
```
