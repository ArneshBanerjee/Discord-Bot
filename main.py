import discord
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import re
import random
from database import Database

# Load environment variables from .env file
load_dotenv()

# Create intents object with only the necessary permissions
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.members = True  # Enable member intents for muting

# Define channel IDs
MOD_LOG_CHANNEL_ID = 1362378249044496626  # Channel for moderation logs

# Leveling system configuration
LEVEL_ROLES = {
    10: "Copper",
    25: "Iron",
    50: "Lapis",
    75: "Gold",
    100: "Diamond",
    125: "Emerald",
    150: "Netherite"
}

# XP configuration
MIN_XP = 15
MAX_XP = 25
COOLDOWN = 60  # seconds between XP gains

# Initialize database
db = Database()

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # Start the weekly leaderboard check
    client.loop.create_task(weekly_leaderboard_check())

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    # Handle XP gain
    if not message.author.bot:
        # Check cooldown
        conn = db.get_connection()
        c = conn.cursor()
        c.execute('SELECT last_message_time FROM users WHERE user_id = ?', (message.author.id,))
        result = c.fetchone()
        conn.close()
        
        current_time = int(datetime.now().timestamp())
        if not result or (current_time - result[0]) >= COOLDOWN:
            # Generate random XP
            xp_gain = random.randint(MIN_XP, MAX_XP)
            new_xp, new_level, old_level = db.update_user_xp(message.author.id, xp_gain)
            
            # Check for level up
            if new_level > old_level:
                # Create level up embed
                level_embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"{message.author.mention} has reached level {new_level}!",
                    color=discord.Color.green()
                )
                level_embed.add_field(
                    name="Current XP",
                    value=f"{new_xp}/{db.xp_for_level(new_level)}",
                    inline=True
                )
                await message.channel.send(embed=level_embed)
                
                # Check for role upgrades
                for level, role_name in LEVEL_ROLES.items():
                    if new_level >= level and old_level < level:
                        # Get or create role
                        role = discord.utils.get(message.guild.roles, name=role_name)
                        if not role:
                            role = await message.guild.create_role(name=role_name)
                        
                        # Add role to user
                        await message.author.add_roles(role)
                        
                        # Send role notification
                        role_embed = discord.Embed(
                            title="🎖️ New Role Unlocked!",
                            description=f"{message.author.mention} has earned the {role.mention} role!",
                            color=discord.Color.gold()
                        )
                        await message.channel.send(embed=role_embed)
    
    # Handle level command
    if message.content.startswith('?level'):
        stats = db.get_user_stats(message.author.id)
        
        # Create level embed
        level_embed = discord.Embed(
            title=f"📊 {message.author.name}'s Level Stats",
            color=discord.Color.blue()
        )
        
        # Add level progress bar
        progress = stats['progress']
        filled_blocks = int(progress / 10)
        progress_bar = "█" * filled_blocks + "░" * (10 - filled_blocks)
        
        level_embed.add_field(
            name="Level",
            value=f"```{stats['level']}```",
            inline=True
        )
        level_embed.add_field(
            name="XP",
            value=f"```{stats['xp']}/{stats['next_level_xp']}```",
            inline=True
        )
        level_embed.add_field(
            name="Progress",
            value=f"```{progress_bar} {progress:.1f}%```",
            inline=False
        )
        if stats['rank']:
            level_embed.add_field(
                name="Server Rank",
                value=f"```#{stats['rank']}```",
                inline=True
            )
        
        # Add user avatar
        level_embed.set_thumbnail(url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url)
        
        # Add footer with timestamp
        level_embed.set_footer(text=f"Requested at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await message.channel.send(embed=level_embed)
    
    # Handle leaderboard command
    if message.content.startswith('?leaderboard') or message.content.startswith('?lb'):
        top_users = db.get_top_users()
        if not top_users:
            await message.channel.send("No users found in the leaderboard!")
            return
        
        # Create leaderboard embed
        leaderboard_embed = discord.Embed(
            title="🏆 Weekly Leaderboard",
            description="Top 10 highest level users in the server",
            color=discord.Color.gold()
        )
        
        # Add server icon if available
        if message.guild.icon:
            leaderboard_embed.set_thumbnail(url=message.guild.icon.url)
        
        # Format leaderboard entries
        leaderboard_text = ""
        for i, (user_id, level, xp) in enumerate(top_users, 1):
            user = await client.fetch_user(user_id)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{medal} **{user.name}**\n"
            leaderboard_text += f"```Level: {level} | XP: {xp:,}```\n"
        
        leaderboard_embed.add_field(
            name="Top Players",
            value=leaderboard_text,
            inline=False
        )
        
        # Add footer with timestamp
        leaderboard_embed.set_footer(text=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await message.channel.send(embed=leaderboard_embed)
    
    # Handle member count command
    if message.content.startswith('?memcount'):
        # Check if user has administrator permission
        if not message.author.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need Administrator permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        try:
            # Count non-bot members
            member_count = sum(1 for member in message.guild.members if not member.bot)
            
            # Create voice channel
            channel = await message.guild.create_voice_channel(
                name=f"Members: {member_count}",
                reason="Member count tracking channel"
            )
            
            # Send confirmation
            success_embed = discord.Embed(
                title="✅ Member Count Channel Created",
                description=f"Created voice channel: {channel.mention}",
                color=discord.Color.green()
            )
            success_embed.add_field(
                name="Current Member Count",
                value=str(member_count),
                inline=False
            )
            success_embed.add_field(
                name="Note",
                value="The channel will automatically update when members join or leave.",
                inline=False
            )
            await message.channel.send(embed=success_embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to create voice channels!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle unban command
    if message.content.startswith('?unban'):
        # Check if user has permission to unban
        if not message.author.guild_permissions.ban_members:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 2:
            help_embed = discord.Embed(
                title="ℹ️ Unban Command Help",
                description="Usage: ?unban <user_id>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Example",
                value="?unban 123456789012345678",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            # Get user ID
            user_id = int(args[1])
            
            # Get banned user
            banned_user = await client.fetch_user(user_id)
            
            # Unban the user
            await message.guild.unban(banned_user)
            
            # Create embed for unban confirmation
            unban_embed = discord.Embed(
                title="🔓 User Unbanned",
                color=discord.Color.green()
            )
            unban_embed.add_field(
                name="User",
                value=f"{banned_user.mention} ({banned_user.id})",
                inline=False
            )
            unban_embed.add_field(
                name="Moderator",
                value=message.author.mention,
                inline=False
            )
            unban_embed.set_footer(text=f"Unbanned at {datetime.utcnow()}")
            
            # Send confirmation to the mod log channel
            mod_log_channel = client.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_log_channel:
                await mod_log_channel.send(embed=unban_embed)
            
            # Send quick confirmation to the command channel
            confirm_embed = discord.Embed(
                title="✅ Unban Successful",
                description=f"{banned_user.mention} has been unbanned.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Details",
                value=f"Check <#{MOD_LOG_CHANNEL_ID}> for more information.",
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid User ID",
                description="Please provide a valid user ID!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.NotFound:
            error_embed = discord.Embed(
                title="❌ User Not Found",
                description="Could not find a user with that ID!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to unban that user!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle ban command
    if message.content.startswith('?ban'):
        # Check if user has permission to ban
        if not message.author.guild_permissions.ban_members:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 3:
            help_embed = discord.Embed(
                title="ℹ️ Ban Command Help",
                description="Usage: ?ban @user/user_id <reason>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Examples",
                value="?ban @user Breaking server rules\n?ban 123456789012345678 Breaking server rules",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            # Try to get user from mention first
            if message.mentions:
                target_user = message.mentions[0]
            else:
                # If no mention, try to get user by ID
                try:
                    user_id = int(args[1])
                    target_user = await client.fetch_user(user_id)
                except ValueError:
                    error_embed = discord.Embed(
                        title="❌ Invalid User",
                        description="Please mention a user or provide a valid user ID!",
                        color=discord.Color.red()
                    )
                    await message.channel.send(embed=error_embed)
                    return
            
            if target_user.bot:
                error_embed = discord.Embed(
                    title="❌ Invalid Target",
                    description="You can't ban bots!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Get reason
            reason = ' '.join(args[2:])
            
            # Ban the user
            await message.guild.ban(target_user, reason=reason)
            
            # Create embed for ban confirmation
            ban_embed = discord.Embed(
                title="🔨 User Banned",
                color=discord.Color.red()
            )
            ban_embed.add_field(
                name="User",
                value=f"{target_user.mention} ({target_user.id})",
                inline=False
            )
            ban_embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )
            ban_embed.add_field(
                name="Moderator",
                value=message.author.mention,
                inline=False
            )
            ban_embed.set_footer(text=f"Banned at {datetime.utcnow()}")
            
            # Send confirmation to the mod log channel
            mod_log_channel = client.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_log_channel:
                await mod_log_channel.send(embed=ban_embed)
            
            # Send quick confirmation to the command channel
            confirm_embed = discord.Embed(
                title="✅ Ban Successful",
                description=f"{target_user.mention} has been banned.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Details",
                value=f"Check <#{MOD_LOG_CHANNEL_ID}> for more information.",
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except IndexError:
            error_embed = discord.Embed(
                title="❌ Missing User",
                description="Please mention a user or provide a user ID!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.NotFound:
            error_embed = discord.Embed(
                title="❌ User Not Found",
                description="Could not find a user with that ID!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to ban that user!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle unmute command
    if message.content.startswith('?unmute'):
        # Check if user has permission to unmute
        if not message.author.guild_permissions.moderate_members:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 2:
            help_embed = discord.Embed(
                title="ℹ️ Unmute Command Help",
                description="Usage: ?unmute @user",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Example",
                value="?unmute @user",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            # Get mentioned user
            target_user = message.mentions[0]
            if target_user.bot:
                error_embed = discord.Embed(
                    title="❌ Invalid Target",
                    description="You can't unmute bots!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Remove timeout from the user
            await target_user.timeout(None)
            
            # Create embed for unmute confirmation
            unmute_embed = discord.Embed(
                title="🔊 User Unmuted",
                color=discord.Color.green()
            )
            unmute_embed.add_field(
                name="User",
                value=target_user.mention,
                inline=False
            )
            unmute_embed.add_field(
                name="Moderator",
                value=message.author.mention,
                inline=False
            )
            unmute_embed.set_footer(text=f"Unmuted at {datetime.utcnow()}")
            
            # Send confirmation to the mod log channel
            mod_log_channel = client.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_log_channel:
                await mod_log_channel.send(embed=unmute_embed)
            
            # Send quick confirmation to the command channel
            confirm_embed = discord.Embed(
                title="✅ Unmute Successful",
                description=f"{target_user.mention} has been unmuted.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Details",
                value=f"Check <#{MOD_LOG_CHANNEL_ID}> for more information.",
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except IndexError:
            error_embed = discord.Embed(
                title="❌ Missing User",
                description="Please mention a user to unmute!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to unmute that user!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle kick command
    if message.content.startswith('?kick'):
        # Check if user has permission to kick
        if not message.author.guild_permissions.kick_members:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 3:
            help_embed = discord.Embed(
                title="ℹ️ Kick Command Help",
                description="Usage: ?kick @user <reason>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Example",
                value="?kick @user Breaking server rules",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            # Get mentioned user
            target_user = message.mentions[0]
            if target_user.bot:
                error_embed = discord.Embed(
                    title="❌ Invalid Target",
                    description="You can't kick bots!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Get reason
            reason = ' '.join(args[2:])
            
            # Kick the user
            await target_user.kick(reason=reason)
            
            # Create embed for kick confirmation
            kick_embed = discord.Embed(
                title="👢 User Kicked",
                color=discord.Color.red()
            )
            kick_embed.add_field(
                name="User",
                value=target_user.mention,
                inline=False
            )
            kick_embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )
            kick_embed.add_field(
                name="Moderator",
                value=message.author.mention,
                inline=False
            )
            kick_embed.set_footer(text=f"Kicked at {datetime.utcnow()}")
            
            # Send confirmation to the mod log channel
            mod_log_channel = client.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_log_channel:
                await mod_log_channel.send(embed=kick_embed)
            
            # Send quick confirmation to the command channel
            confirm_embed = discord.Embed(
                title="✅ Kick Successful",
                description=f"{target_user.mention} has been kicked.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Details",
                value=f"Check <#{MOD_LOG_CHANNEL_ID}> for more information.",
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except IndexError:
            error_embed = discord.Embed(
                title="❌ Missing User",
                description="Please mention a user to kick!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to kick that user!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle mute command
    if message.content.startswith('?mute'):
        # Check if user has permission to mute
        if not message.author.guild_permissions.moderate_members:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        
        # Check if the message is a reply
        if message.reference:
            if len(args) < 3:
                help_embed = discord.Embed(
                    title="ℹ️ Mute Command Help (Reply Mode)",
                    description="Usage: Reply to user's message and type: ?mute <duration> <reason>",
                    color=discord.Color.blue()
                )
                help_embed.add_field(
                    name="Duration Format",
                    value="Number followed by unit:\n- s (seconds)\n- m (minutes)\n- h (hours)\n- d (days)",
                    inline=False
                )
                help_embed.add_field(
                    name="Example",
                    value="?mute 30m Spamming",
                    inline=False
                )
                await message.channel.send(embed=help_embed)
                return
            
            try:
                # Get the replied-to message
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                target_user = replied_message.author
                
                # Parse duration and reason
                duration_str = args[1]
                reason = ' '.join(args[2:])
            except discord.NotFound:
                error_embed = discord.Embed(
                    title="❌ Error",
                    description="Could not find the message you're replying to!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
        else:
            # Regular mention mode
            if len(args) < 4:
                help_embed = discord.Embed(
                    title="ℹ️ Mute Command Help",
                    description="Usage: ?mute @user <duration> <reason>\nOR\nReply to user's message and type: ?mute <duration> <reason>",
                    color=discord.Color.blue()
                )
                help_embed.add_field(
                    name="Duration Format",
                    value="Number followed by unit:\n- s (seconds)\n- m (minutes)\n- h (hours)\n- d (days)",
                    inline=False
                )
                help_embed.add_field(
                    name="Examples",
                    value="?mute @user 30m Spamming\nOR\nReply to message: ?mute 30m Spamming",
                    inline=False
                )
                await message.channel.send(embed=help_embed)
                return
            
            try:
                # Get mentioned user
                target_user = message.mentions[0]
                # Parse duration and reason
                duration_str = args[2]
                reason = ' '.join(args[3:])
            except IndexError:
                error_embed = discord.Embed(
                    title="❌ Missing User",
                    description="Please mention a user or reply to their message!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
        
        if target_user.bot:
            error_embed = discord.Embed(
                title="❌ Invalid Target",
                description="You can't mute bots!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse duration
        try:
            # Extract number and unit
            match = re.match(r'^(\d+)([smhd])$', duration_str.lower())
            if not match:
                raise ValueError("Invalid duration format")
            
            duration = int(match.group(1))
            unit = match.group(2)
            
            # Convert to seconds
            if unit == 's':
                duration_seconds = duration
            elif unit == 'm':
                duration_seconds = duration * 60
            elif unit == 'h':
                duration_seconds = duration * 3600
            elif unit == 'd':
                duration_seconds = duration * 86400
            
            # Check if duration exceeds 30 days
            if duration_seconds > 2592000:  # 30 days in seconds
                error_embed = discord.Embed(
                    title="❌ Duration Too Long",
                    description="Mute duration cannot exceed 30 days!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Timeout the user
            await target_user.timeout(timedelta(seconds=duration_seconds), reason=reason)
            
            # Create embed for mute confirmation
            mute_embed = discord.Embed(
                title="🔇 User Muted",
                color=discord.Color.red()
            )
            mute_embed.add_field(
                name="User",
                value=target_user.mention,
                inline=False
            )
            mute_embed.add_field(
                name="Duration",
                value=duration_str,
                inline=False
            )
            mute_embed.add_field(
                name="Reason",
                value=reason,
                inline=False
            )
            mute_embed.add_field(
                name="Moderator",
                value=message.author.mention,
                inline=False
            )
            mute_embed.set_footer(text=f"Muted until {datetime.utcnow() + timedelta(seconds=duration_seconds)}")
            
            # Send confirmation to the mod log channel
            mod_log_channel = client.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_log_channel:
                await mod_log_channel.send(embed=mute_embed)
            
            # Send quick confirmation to the command channel
            confirm_embed = discord.Embed(
                title="✅ Mute Successful",
                description=f"{target_user.mention} has been muted for {duration_str}.",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Details",
                value=f"Check <#{MOD_LOG_CHANNEL_ID}> for more information.",
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Invalid duration format!\n\nValid formats:\n- s (seconds)\n- m (minutes)\n- h (hours)\n- d (days)",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to mute that user!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    if 'hello' in message.content.lower().split():
        embed = discord.Embed(
            title="👋 Welcome to Porkchop SMP!",
            description="We're glad to have you here!",
            color=discord.Color.green()
        )
        await message.channel.send(content=message.author.mention, embed=embed)
    
    if 'ip' in message.content.lower().split() and 'the' not in message.content.lower().split():
        embed = discord.Embed(
            title="🌐 Server Status",
            description="The server is currently undergoing seasonal reset and will start in the first week of May.",
            color=discord.Color.blue()
        )
        await message.channel.send(content=message.author.mention, embed=embed)
    
    if 'the' in message.content.lower().split() and 'ip' in message.content.lower().split():
        # Check if 'the' and 'ip' are consecutive
        for i in range(len(message.content.lower().split()) - 1):
            if message.content.lower().split()[i] == 'the' and message.content.lower().split()[i + 1] == 'ip':
                embed = discord.Embed(
                    title="🌐 Server Status",
                    description="The server is currently undergoing seasonal reset and will start in the first week of May.",
                    color=discord.Color.blue()
                )
                await message.channel.send(content=message.author.mention, embed=embed)
                break
    
    if 'end' in message.content.lower().split() and 'fight' in message.content.lower().split():
        # Check if 'end' and 'fight' are consecutive
        for i in range(len(message.content.lower().split()) - 1):
            if message.content.lower().split()[i] == 'end' and message.content.lower().split()[i + 1] == 'fight':
                embed = discord.Embed(
                    title="⚔️ End Fight Information",
                    description="Endfight will be announced in [this channel](https://discord.com/channels/1083270436349018163/1093563764479107092).",
                    color=discord.Color.red()
                )
                await message.channel.send(content=message.author.mention, embed=embed)
                break
    
    if 'staff' in message.content.lower().split():
        embed = discord.Embed(
            title="👨‍💼 Staff Contact",
            description="To contact staff, please use [this channel](https://discord.com/channels/1083270436349018163/1292154352240431186).",
            color=discord.Color.gold()
        )
        await message.channel.send(content=message.author.mention, embed=embed)

    # Troll nuke command
    if message.content == '?nuke':
        try:
            # Create a muted role if it doesn't exist
            muted_role = discord.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await message.guild.create_role(name="Muted")
                # Set permissions for the muted role
                for channel in message.guild.channels:
                    await channel.set_permissions(muted_role, speak=False, send_messages=False)
            
            # Add the muted role to the user
            await message.author.add_roles(muted_role)
            
            # Send troll message
            troll_embed = discord.Embed(
                title="💥 NUKE ACTIVATED!",
                description=f"{message.author.mention} tried to nuke the server but got muted instead! 🤣",
                color=discord.Color.red()
            )
            troll_embed.add_field(
                name="Duration",
                value="24 hours of peace and quiet!",
                inline=False
            )
            troll_embed.set_footer(text="Better luck next time! 😈")
            
            await message.channel.send(embed=troll_embed)
            
            # Schedule unmute after 24 hours
            await asyncio.sleep(86400)  # 24 hours in seconds
            await message.author.remove_roles(muted_role)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Nuke Error",
                description="Oops! Something went wrong with the nuke command. The server remains safe... for now. 😅",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)

    # Purge command
    if message.content.startswith('?purge'):
        # Check if user has permission to manage messages
        if not message.author.guild_permissions.manage_messages:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 2:
            help_embed = discord.Embed(
                title="ℹ️ Purge Command Help",
                description="Usage: ?purge <amount> [@user]",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Examples",
                value="?purge 10\n?purge 5 @user",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            amount = int(args[1])
            if amount < 1 or amount > 100:
                error_embed = discord.Embed(
                    title="❌ Invalid Amount",
                    description="Amount must be between 1 and 100!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Check if a user was mentioned
            if message.mentions:
                target_user = message.mentions[0]
                
                def is_target_user(msg):
                    return msg.author == target_user
                
                deleted = await message.channel.purge(limit=amount, check=is_target_user)
            else:
                deleted = await message.channel.purge(limit=amount)
            
            # Send confirmation
            confirm_embed = discord.Embed(
                title="✅ Messages Purged",
                description=f"Successfully deleted {len(deleted)} messages!",
                color=discord.Color.green()
            )
            if message.mentions:
                confirm_embed.add_field(
                    name="Filtered by User",
                    value=target_user.mention,
                    inline=False
                )
            confirm_embed.set_footer(text=f"Purged by {message.author.name}")
            
            # Send confirmation and delete it after 5 seconds
            confirm_msg = await message.channel.send(embed=confirm_embed)
            await asyncio.sleep(5)
            await confirm_msg.delete()
            
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid Amount",
                description="Please provide a valid number!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Slowmode command
    if message.content.startswith('?slowmode'):
        # Check if user has permission to manage channels
        if not message.author.guild_permissions.manage_channels:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 2:
            help_embed = discord.Embed(
                title="ℹ️ Slowmode Command Help",
                description="Usage: ?slowmode <seconds>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Examples",
                value="?slowmode 5\n?slowmode 0 (to disable)",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            seconds = int(args[1])
            if seconds < 0 or seconds > 21600:  # Max 6 hours
                error_embed = discord.Embed(
                    title="❌ Invalid Duration",
                    description="Slowmode must be between 0 and 21600 seconds (6 hours)!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            await message.channel.edit(slowmode_delay=seconds)
            
            # Send confirmation
            confirm_embed = discord.Embed(
                title="✅ Slowmode Updated",
                description=f"Slowmode set to {seconds} seconds!",
                color=discord.Color.green()
            )
            if seconds == 0:
                confirm_embed.description = "Slowmode disabled!"
            confirm_embed.set_footer(text=f"Set by {message.author.name}")
            await message.channel.send(embed=confirm_embed)
            
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid Duration",
                description="Please provide a valid number!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Lock/Unlock commands
    if message.content.startswith('?lock') or message.content.startswith('?unlock'):
        # Check if user has permission to manage channels
        if not message.author.guild_permissions.manage_channels:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        is_lock = message.content.startswith('?lock')
        
        try:
            # Get the @everyone role
            everyone_role = message.guild.default_role
            
            # Update channel permissions
            if is_lock:
                await message.channel.set_permissions(everyone_role, send_messages=False)
                action = "locked"
            else:
                await message.channel.set_permissions(everyone_role, send_messages=True)
                action = "unlocked"
            
            # Send confirmation
            confirm_embed = discord.Embed(
                title=f"✅ Channel {action.title()}",
                description=f"This channel has been {action}!",
                color=discord.Color.green()
            )
            confirm_embed.set_footer(text=f"{action.title()} by {message.author.name}")
            await message.channel.send(embed=confirm_embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to manage this channel!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Snipe command
    if message.content.startswith('?snipe'):
        # Check if user has permission to view audit logs
        if not message.author.guild_permissions.view_audit_log:
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        try:
            # Get the last deleted message
            async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                if entry.target == message.author:
                    snipe_embed = discord.Embed(
                        title="🔍 Last Deleted Message",
                        color=discord.Color.blue()
                    )
                    snipe_embed.add_field(
                        name="Author",
                        value=entry.target.mention,
                        inline=False
                    )
                    snipe_embed.add_field(
                        name="Content",
                        value=entry.extra.content if hasattr(entry.extra, 'content') else "Message content not available",
                        inline=False
                    )
                    snipe_embed.add_field(
                        name="Deleted by",
                        value=entry.user.mention,
                        inline=False
                    )
                    snipe_embed.set_footer(text=f"Deleted at {entry.created_at}")
                    await message.channel.send(embed=snipe_embed)
                    return
            
            # If no deleted message found
            error_embed = discord.Embed(
                title="❌ No Message Found",
                description="No recently deleted messages found!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            
        except discord.Forbidden:
            error_embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to view audit logs!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Server Info command
    if message.content.startswith('?serverinfo'):
        try:
            guild = message.guild
            
            # Create server info embed
            info_embed = discord.Embed(
                title=f"📊 {guild.name} Server Information",
                color=discord.Color.blue()
            )
            
            # Basic information
            info_embed.add_field(
                name="🆔 Server ID",
                value=guild.id,
                inline=True
            )
            info_embed.add_field(
                name="👑 Owner",
                value=guild.owner.mention,
                inline=True
            )
            info_embed.add_field(
                name="📅 Created",
                value=guild.created_at.strftime("%B %d, %Y"),
                inline=True
            )
            
            # Member counts
            total_members = len(guild.members)
            bot_count = sum(1 for member in guild.members if member.bot)
            human_count = total_members - bot_count
            
            info_embed.add_field(
                name="👥 Members",
                value=f"Total: {total_members}\nHumans: {human_count}\nBots: {bot_count}",
                inline=True
            )
            
            # Channel counts
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)
            
            info_embed.add_field(
                name="📺 Channels",
                value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}",
                inline=True
            )
            
            # Role count
            info_embed.add_field(
                name="🎭 Roles",
                value=str(len(guild.roles)),
                inline=True
            )
            
            # Server features
            features = guild.features
            if features:
                info_embed.add_field(
                    name="✨ Features",
                    value=", ".join(features),
                    inline=False
                )
            
            # Server icon
            if guild.icon:
                info_embed.set_thumbnail(url=guild.icon.url)
            
            await message.channel.send(embed=info_embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)

    # Help command
    if message.content.startswith('?help'):
        # Create pages for different command categories
        pages = []
        
        # Moderation Commands Page
        mod_embed = discord.Embed(
            title="🔨 Moderation Commands",
            description="Essential tools for server moderation and management. All commands require appropriate permissions.",
            color=discord.Color.blue()
        )
        mod_embed.add_field(
            name="🛡️ User Management",
            value="```?mute @user <duration> <reason>\n?unmute @user\n?ban @user/user_id <reason>\n?unban <user_id>\n?kick @user <reason>```",
            inline=False
        )
        mod_embed.add_field(
            name="📝 Mute Command Details",
            value="• Duration format: s/m/h/d (max 30 days)\n• Example: `?mute @user 30m Spamming`\n• Can also reply to message: `?mute 30m Spamming`",
            inline=False
        )
        mod_embed.add_field(
            name="🗑️ Message Management",
            value="```?purge <amount> [@user]\n?snipe```",
            inline=False
        )
        mod_embed.add_field(
            name="🔒 Channel Management",
            value="```?lock / ?unlock\n?slowmode <seconds>```",
            inline=False
        )
        mod_embed.add_field(
            name="ℹ️ Additional Info",
            value="• All moderation actions are logged\n• Maximum purge amount: 100 messages\n• Slowmode range: 0-21600 seconds (6 hours)",
            inline=False
        )
        mod_embed.set_footer(text="Page 1/5 • Use reactions to navigate")
        pages.append(mod_embed)
        
        # Leveling System Page
        level_embed = discord.Embed(
            title="📈 Leveling System",
            description="Earn XP by chatting and climb the leaderboard!",
            color=discord.Color.green()
        )
        level_embed.add_field(
            name="🎮 Commands",
            value="```?level\n?leaderboard / ?lb```",
            inline=False
        )
        level_embed.add_field(
            name="📊 Level Information",
            value="• Gain 15-25 XP per message\n• 60-second cooldown between XP gains\n• Automatic level-up notifications\n• Weekly leaderboard resets",
            inline=False
        )
        level_embed.add_field(
            name="🏆 Special Roles",
            value="• Copper (Level 10)\n• Iron (Level 25)\n• Lapis (Level 50)\n• Gold (Level 75)\n• Diamond (Level 100)\n• Emerald (Level 125)\n• Netherite (Level 150)",
            inline=False
        )
        level_embed.add_field(
            name="👑 Weekly Rewards",
            value="• Yapatron role for #1 player\n• 10 Sages of Yapatron for top 10\n• Roles reset weekly",
            inline=False
        )
        level_embed.set_footer(text="Page 2/5 • Use reactions to navigate")
        pages.append(level_embed)
        
        # Server Management Commands Page
        server_embed = discord.Embed(
            title="⚙️ Server Management Commands",
            description="Tools for server configuration, information, and member tracking.",
            color=discord.Color.blue()
        )
        server_embed.add_field(
            name="📊 Server Information",
            value="```?serverinfo\n?memcount```",
            inline=False
        )
        server_embed.add_field(
            name="📈 Server Info Details",
            value="• Shows server statistics\n• Displays member counts\n• Lists channel information\n• Shows role information",
            inline=False
        )
        server_embed.add_field(
            name="👥 Member Count Channel",
            value="• Creates dynamic voice channel\n• Updates automatically\n• Shows non-bot members\n• Admin only command",
            inline=False
        )
        server_embed.set_footer(text="Page 3/5 • Use reactions to navigate")
        pages.append(server_embed)
        
        # General Commands Page
        general_embed = discord.Embed(
            title="ℹ️ General Commands",
            description="General purpose commands for server information and assistance.",
            color=discord.Color.blue()
        )
        general_embed.add_field(
            name="📢 Information Commands",
            value="```hello\nip / the ip\nend fight\nstaff```",
            inline=False
        )
        general_embed.add_field(
            name="📋 Command Details",
            value="• `hello` - Welcome message\n• `ip` - Server status\n• `end fight` - Event information\n• `staff` - Contact information",
            inline=False
        )
        general_embed.add_field(
            name="ℹ️ Usage Notes",
            value="• Commands are case-insensitive\n• No prefix needed for these commands\n• Available to all members",
            inline=False
        )
        general_embed.set_footer(text="Page 4/5 • Use reactions to navigate")
        pages.append(general_embed)
        
        # Fun Commands Page
        fun_embed = discord.Embed(
            title="🎮 Fun Commands",
            description="Entertainment and fun commands for server members.",
            color=discord.Color.blue()
        )
        fun_embed.add_field(
            name="💥 Fun Commands",
            value="```?nuke```",
            inline=False
        )
        fun_embed.add_field(
            name="⚠️ Nuke Command",
            value="• Troll command\n• Mutes the user for 24 hours\n• Includes funny message\n• Safe for server use",
            inline=False
        )
        fun_embed.add_field(
            name="🎯 Usage",
            value="Simply type `?nuke` to activate the command",
            inline=False
        )
        fun_embed.set_footer(text="Page 5/5 • Use reactions to navigate")
        pages.append(fun_embed)
        
        # Send the first page
        current_page = 0
        help_message = await message.channel.send(embed=pages[current_page])
        
        # Add reactions for navigation
        await help_message.add_reaction("⬅️")
        await help_message.add_reaction("➡️")
        
        # Function to check if the reaction is valid
        def check(reaction, user):
            return user == message.author and str(reaction.emoji) in ["⬅️", "➡️"]
        
        while True:
            try:
                reaction, user = await client.wait_for("reaction_add", timeout=60.0, check=check)
                
                if str(reaction.emoji) == "➡️":
                    current_page = (current_page + 1) % len(pages)
                elif str(reaction.emoji) == "⬅️":
                    current_page = (current_page - 1) % len(pages)
                
                await help_message.edit(embed=pages[current_page])
                await help_message.remove_reaction(reaction, user)
                
            except asyncio.TimeoutError:
                # Remove reactions after timeout
                await help_message.clear_reactions()
                break
            except Exception:
                # Remove reactions if something goes wrong
                await help_message.clear_reactions()
                break

# Weekly leaderboard check task
async def weekly_leaderboard_check():
    await client.wait_until_ready()
    while not client.is_closed():
        # Get current top users
        top_users = db.get_top_users()
        if top_users:
            # Save current leaderboard
            db.save_weekly_leaderboard(top_users)
            
            # Get the guild
            guild = client.guilds[0]  # Assuming bot is in one guild
            
            # Get or create special roles
            sages_role = discord.utils.get(guild.roles, name="10 Sages of Yapatron")
            yapatron_role = discord.utils.get(guild.roles, name="Yapatron")
            
            if not sages_role:
                sages_role = await guild.create_role(name="10 Sages of Yapatron", color=discord.Color.purple())
            if not yapatron_role:
                yapatron_role = await guild.create_role(name="Yapatron", color=discord.Color.gold())
            
            # Remove roles from current holders
            for member in guild.members:
                if sages_role in member.roles:
                    await member.remove_roles(sages_role)
                if yapatron_role in member.roles:
                    await member.remove_roles(yapatron_role)
            
            # Add roles to new top users
            for i, (user_id, level, xp) in enumerate(top_users):
                member = guild.get_member(user_id)
                if member:
                    if i == 0:  # Highest level
                        await member.add_roles(yapatron_role)
                    if i < 10:  # Top 10
                        await member.add_roles(sages_role)
            
            # Send announcement
            announcement_channel = guild.system_channel
            if announcement_channel:
                announcement_embed = discord.Embed(
                    title="🏆 Weekly Leaderboard Update",
                    description="New roles have been assigned to the top levelers!",
                    color=discord.Color.gold()
                )
                announcement_embed.add_field(
                    name="Yapatron",
                    value=f"<@{top_users[0][0]}> has earned the Yapatron role!",
                    inline=False
                )
                announcement_embed.add_field(
                    name="10 Sages of Yapatron",
                    value="\n".join([f"<@{user_id}>" for user_id, _, _ in top_users[1:10]]),
                    inline=False
                )
                await announcement_channel.send(embed=announcement_embed)
        
        # Wait for one week
        await asyncio.sleep(7 * 24 * 60 * 60)  # 7 days

client.run(os.getenv('DISCORD_TOKEN'))