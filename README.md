# PorkBot

PorkBot is a Discord bot designed to manage and moderate the Porkchop SMP server. It includes a variety of commands for moderation, server management, and fun interactions.

## Features
- Moderation commands (mute, unmute, ban, unban, kick, purge, etc.)
- Server management commands (server info, member count, autosend, etc.)
- Fun commands (e.g., `?nuke`)
- Automatic reactions and member tracking

## Commands

### Moderation Commands
- `?mute @user <duration> <reason>` - Temporarily mutes a user.
- `?unmute @user` - Unmutes a user.
- `?ban @user/user_id <reason>` - Bans a user.
- `?unban <user_id>` - Unbans a user.
- `?kick @user <reason>` - Kicks a user.
- `?purge <amount> [@user]` - Deletes a specified number of messages.

### Server Management Commands
- `?serverinfo` - Displays server statistics and information.
- `?memcount` - Creates a dynamic voice channel showing the member count.
- `?autosend <channel_id> <interval> <message>` - Automatically sends a message to a channel at a specified interval.
  - **Interval Format**: Use `m` (minutes), `h` (hours), or `d` (days).
  - **Example**: `?autosend 123456789012345678 1h Hello World!`
- `?autosendstop <channel_id>` - Stops the autosend task for a specific channel.

### General Commands
- `hello` - Sends a welcome message.
- `ip` / `the ip` - Displays server status.
- `end fight` - Provides information about the End Fight event.
- `staff` - Displays staff contact information.

### Fun Commands
- `?nuke` - A troll command that mutes the user for 24 hours with a funny message.

## Setup
1. Clone the repository.
2. Install the required dependencies:
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