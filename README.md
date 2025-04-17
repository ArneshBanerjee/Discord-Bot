# PorkBot - Discord Moderation & Leveling Bot

A feature-rich Discord bot with moderation tools and a leveling system.

## Features

### Moderation Commands
- `?mute` - Mute users with customizable duration
- `?unmute` - Unmute users
- `?ban` - Ban users with reason
- `?unban` - Unban users
- `?kick` - Kick users with reason
- `?purge` - Bulk delete messages
- `?snipe` - View last deleted message
- `?lock`/`?unlock` - Lock/unlock channels
- `?slowmode` - Set channel slowmode

### Leveling System
- Automatic XP gain from chatting
- Level roles (Copper, Iron, Lapis, Gold, Diamond, Emerald, Netherite)
- Weekly leaderboard with special roles
- `?level` - Check your level stats
- `?leaderboard`/`?lb` - View server leaderboard

### Server Management
- `?serverinfo` - View server statistics
- `?memcount` - Create member count voice channel

### General Commands
- Welcome messages
- Server status
- Staff contact
- Event information

## Setup

1. Clone the repository:
```bash
git clone https://github.com/ArneshBanerjee/PorkBot.git
cd PorkBot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your bot token:
```
DISCORD_TOKEN=your_bot_token_here
```

4. Run the bot:
```bash
python main.py
```

## Deployment

This bot can be deployed on various platforms:

### Railway.app (Recommended)
1. Create a new project on Railway
2. Connect your GitHub repository
3. Add your `DISCORD_TOKEN` in the Variables section
4. Deploy!

### Other Options
- Replit
- Heroku
- DigitalOcean
- Oracle Cloud Free Tier

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 