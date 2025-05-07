import discord
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
import re
import random

# Load environment variables from .env file
load_dotenv()

# Create intents object with only the necessary permissions
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.members = True  # Enable member intents for muting

# Define channel IDs
MOD_LOG_CHANNEL_ID = 1094940763441336340  # Channel for moderation logs

# Define role IDs and their permissions
ROLE_PERMISSIONS = {
    # Tier 1: Basic moderation (mute/unmute only)
    1322109984036622346: ['mute', 'unmute'],
    
    # Tier 2: Moderate moderation (mute, unmute, purge, kick)
    1322099468480417832: ['mute', 'unmute', 'purge', 'kick'],
    
    # Tier 3: Advanced moderation (mute, unmute, kick, ban, unban, purge)
    1322098045613248563: ['mute', 'unmute', 'kick', 'ban', 'unban', 'purge'],
    
    # Tier 4: Full access (all commands)
    1322094447030177863: ['*'],
    1322091136059310100: ['*'],
    1330618191050969129: ['*'],
    1322090684810924033: ['*']
}

# Store reaction rules
reaction_rules = {}

# Store active autosend tasks
autosend_tasks = {}

client = discord.Client(intents=intents)

def has_command_permission(member, command):
    """Check if a member has permission to use a specific command."""
    # Get all role IDs the member has
    member_role_ids = [role.id for role in member.roles]
    
    # Check each role's permissions
    for role_id in member_role_ids:
        if role_id in ROLE_PERMISSIONS:
            permissions = ROLE_PERMISSIONS[role_id]
            # If role has full access or specific command permission
            if '*' in permissions or command in permissions:
                return True
    
    return False

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    
    # Set custom status
    activity = discord.Activity(
        type=discord.ActivityType.watching,  # You can change this to playing, listening, etc.
        name="over Porkchop SMP"  # Custom status text
    )
    await client.change_presence(activity=activity, status=discord.Status.online)
    
    # Set about me
    about_me = {
        "name": "PorkBot",
        "description": "Made by <@799190402896494612> to guard Porkchop SMP. Join today discord.gg/porkchopsmp.",
        "version": "1.0.0",
        "features": [
            "Moderation commands",
            "Server management",
            "Automatic reactions",
            "Member tracking"
        ]
    }
    
    # You can access this information later if needed
    client.about_me = about_me

# Add a dictionary to track the last "hello" response time for each user
last_hello_time = {}

# Add a dictionary to track the last report time for each user
last_report_time = {}

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Handle report command
    if message.content.startswith('?report'):
        # Check if the message is a reply
        if not message.reference:
            error_embed = discord.Embed(
                title="❌ Invalid Usage",
                description="You must reply to a message to report it!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return

        # Check if the user is on cooldown
        user_id = message.author.id
        current_time = datetime.utcnow()
        if user_id in last_report_time:
            time_since_last_report = (current_time - last_report_time[user_id]).total_seconds()
            if time_since_last_report < 1800:  # 1800 seconds = 30 minutes
                cooldown_embed = discord.Embed(
                    title="⏳ Cooldown Active",
                    description="You can only make one report every 30 minutes.",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=cooldown_embed)
                return

        # Update the last report time for the user
        last_report_time[user_id] = current_time

        # Get the replied-to message
        try:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
        except discord.NotFound:
            error_embed = discord.Embed(
                title="❌ Error",
                description="Could not find the message you're replying to!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return

        # Parse the reason
        args = message.content.split(maxsplit=1)
        if len(args) < 2:
            error_embed = discord.Embed(
                title="❌ Missing Reason",
                description="You must provide a reason for the report!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        reason = args[1]

        # Get the report channel
        report_channel = client.get_channel(1362287716460396675)
        if not report_channel:
            error_embed = discord.Embed(
                title="❌ Error",
                description="Report channel not found!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return

        # Create the report embed
        report_embed = discord.Embed(
            title="🚨 New Report",
            description=f"**Reported Message:**\n{replied_message.content}",
            color=discord.Color.red()
        )
        report_embed.add_field(
            name="Reporter",
            value=message.author.mention,
            inline=False
        )
        report_embed.add_field(
            name="Reported User",
            value=replied_message.author.mention,
            inline=False
        )
        report_embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )
        report_embed.add_field(
            name="Message Link",
            value=f"[Jump to Message]({replied_message.jump_url})",
            inline=False
        )
        report_embed.set_footer(text=f"Reported at {datetime.utcnow()}")

        # Send the report to the report channel
        await report_channel.send(embed=report_embed)

        # Confirm the report to the reporter
        confirm_embed = discord.Embed(
            title="✅ Report Submitted",
            description="Your report has been submitted successfully.",
            color=discord.Color.green()
        )
        await message.channel.send(embed=confirm_embed)

    # Handle "hello" command with a 5-minute cooldown per user
    if 'hello' in message.content.lower().split():
        user_id = message.author.id
        current_time = datetime.utcnow()

        # Check if the user is in the last_hello_time dictionary
        if user_id in last_hello_time:
            time_since_last_hello = (current_time - last_hello_time[user_id]).total_seconds()
            if time_since_last_hello < 300:  # 300 seconds = 5 minutes
                return  # Ignore the message if it's within the cooldown period

        # Update the last_hello_time for the user
        last_hello_time[user_id] = current_time

        # Send the "hello" response
        embed = discord.Embed(
            title="👋 Welcome to Porkchop SMP!",
            description="We're glad to have you here!",
            color=discord.Color.green()
        )
        await message.channel.send(content=message.author.mention, embed=embed)

    # Check for reaction rules
    for target, emoji in reaction_rules.items():
        # Check if message mentions the target user
        if message.mentions:
            for mention in message.mentions:
                if target.lower() in mention.name.lower() or target.lower() in str(mention.id):
                    try:
                        await message.add_reaction(emoji)
                    except discord.HTTPException:
                        pass
        
        # Check if message contains the target name
        if target.lower() in message.content.lower():
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                pass
    
    # Handle reaction rule commands
    if message.content.startswith('?reaction'):
        if not has_command_permission(message.author, 'reaction'):
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        args = message.content.split()
        if len(args) < 2:
            help_embed = discord.Embed(
                title="ℹ️ Reaction Command Help",
                description="Usage: ?reaction <add/remove/list> [target] [emoji]",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Commands",
                value="```?reaction add <target> <emoji>\n?reaction remove <target>\n?reaction list```",
                inline=False
            )
            help_embed.add_field(
                name="Examples",
                value="?reaction add @user 😊\n?reaction add username 😊\n?reaction remove @user\n?reaction list",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        command = args[1].lower()
        
        if command == "add":
            if len(args) < 4:
                error_embed = discord.Embed(
                    title="❌ Missing Arguments",
                    description="Usage: ?reaction add <target> <emoji>",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            target = args[2]
            emoji = args[3]
            
            # If target is a mention, extract the user ID
            if target.startswith('<@') and target.endswith('>'):
                target = target.strip('<@!>')
            
            reaction_rules[target] = emoji
            
            success_embed = discord.Embed(
                title="✅ Reaction Rule Added",
                description=f"Added reaction rule for '{target}' with emoji {emoji}",
                color=discord.Color.green()
            )
            await message.channel.send(embed=success_embed)
            
        elif command == "remove":
            if len(args) < 3:
                error_embed = discord.Embed(
                    title="❌ Missing Arguments",
                    description="Usage: ?reaction remove <target>",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            target = args[2]
            
            # If target is a mention, extract the user ID
            if target.startswith('<@') and target.endswith('>'):
                target = target.strip('<@!>')
            
            if target in reaction_rules:
                del reaction_rules[target]
                success_embed = discord.Embed(
                    title="✅ Reaction Rule Removed",
                    description=f"Removed reaction rule for '{target}'",
                    color=discord.Color.green()
                )
            else:
                error_embed = discord.Embed(
                    title="❌ Rule Not Found",
                    description=f"No reaction rule found for '{target}'",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            await message.channel.send(embed=success_embed)
            
        elif command == "list":
            if not reaction_rules:
                info_embed = discord.Embed(
                    title="ℹ️ No Reaction Rules",
                    description="There are no active reaction rules.",
                    color=discord.Color.blue()
                )
            else:
                info_embed = discord.Embed(
                    title="ℹ️ Active Reaction Rules",
                    description="Current reaction rules:",
                    color=discord.Color.blue()
                )
                for target, emoji in reaction_rules.items():
                    info_embed.add_field(
                        name=f"Target: {target}",
                        value=f"Emoji: {emoji}",
                        inline=False
                    )
            await message.channel.send(embed=info_embed)
            
        else:
            error_embed = discord.Embed(
                title="❌ Invalid Command",
                description="Valid commands: add, remove, list",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
    
    # Handle member count command
    if message.content.startswith('?memcount'):
        if not has_command_permission(message.author, 'memcount'):
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
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
        if not has_command_permission(message.author, 'unban'):
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
        if not has_command_permission(message.author, 'ban'):
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
        if not has_command_permission(message.author, 'unmute'):
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
        if not has_command_permission(message.author, 'kick'):
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
        if not has_command_permission(message.author, 'mute'):
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
    
    if 'ip' in message.content.lower().split() and 'the' not in message.content.lower().split():
        embed = discord.Embed(
            title="🌐 Server Status",
            description="The ip is `mc.porkchopsmp.online`. Don't forget to claim your free start kits using /kit.",
            color=discord.Color.blue()
        )
        await message.channel.send(content=message.author.mention, embed=embed)
    
    if 'the' in message.content.lower().split() and 'ip' in message.content.lower().split():
        # Check if 'the' and 'ip' are consecutive
        for i in range(len(message.content.lower().split()) - 1):
            if message.content.lower().split()[i] == 'the' and message.content.lower().split()[i + 1] == 'ip':
                embed = discord.Embed(
                    title="🌐 Server Status",
                    description="The ip is `mc.porkchopsmp.online`. Don't forget to claim your free start kits using /kit.",
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
                    description="Endfight will be held on 8th June.",
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
        if not has_command_permission(message.author, 'purge'):
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
        if not has_command_permission(message.author, 'slowmode'):
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
        if not has_command_permission(message.author, 'lock'):
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
        if not has_command_permission(message.author, 'snipe'):
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
        if not has_command_permission(message.author, 'serverinfo'):
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
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
        mod_embed.set_footer(text="Page 1/4 • Use reactions to navigate")
        pages.append(mod_embed)
        
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
        server_embed.set_footer(text="Page 2/4 • Use reactions to navigate")
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
        general_embed.set_footer(text="Page 3/4 • Use reactions to navigate")
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
        fun_embed.set_footer(text="Page 4/4 • Use reactions to navigate")
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

    # Handle about command
    if message.content.startswith('?about'):
        about_embed = discord.Embed(
            title=f"🤖 About {client.about_me['name']}",
            description=client.about_me['description'],
            color=discord.Color.blue()
        )
        about_embed.add_field(
            name="Version",
            value=client.about_me['version'],
            inline=True
        )
        about_embed.add_field(
            name="Features",
            value="\n".join(f"• {feature}" for feature in client.about_me['features']),
            inline=False
        )
        about_embed.add_field(
            name="Status",
            value="Online and watching over Porkchop SMP",
            inline=False
        )
        about_embed.set_footer(text=f"Requested by {message.author.name}")
        await message.channel.send(embed=about_embed)

    # Handle autosend command
    if message.content.startswith('?autosend'):
        # Check if user has permission (only specific roles)
        allowed_roles = [1322091136059310100, 1322090684810924033, 1322094447030177863]
        if not any(role.id in allowed_roles for role in message.author.roles):
            error_embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command!",
                color=discord.Color.red()
            )
            await message.channel.send(embed=error_embed)
            return
        
        # Parse command arguments
        args = message.content.split()
        if len(args) < 4:
            help_embed = discord.Embed(
                title="ℹ️ Autosend Command Help",
                description="Usage: ?autosend <channel_id> <interval> <message>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Interval Format",
                value="Number followed by unit:\n- m (minutes)\n- h (hours)\n- d (days)",
                inline=False
            )
            help_embed.add_field(
                name="Example",
                value="?autosend 123456789012345678 1h Hello World!",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            # Get channel ID
            channel_id = int(args[1])
            channel = client.get_channel(channel_id)
            if not channel:
                error_embed = discord.Embed(
                    title="❌ Invalid Channel",
                    description="Could not find the specified channel!",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                return
            
            # Parse interval
            interval_str = args[2]
            match = re.match(r'^(\d+)([mhd])$', interval_str.lower())
            if not match:
                raise ValueError("Invalid interval format")
            
            interval = int(match.group(1))
            unit = match.group(2)
            
            # Convert to seconds
            if unit == 'm':
                interval_seconds = interval * 60
            elif unit == 'h':
                interval_seconds = interval * 3600
            elif unit == 'd':
                interval_seconds = interval * 86400
            
            # Get message content
            message_content = ' '.join(args[3:])
            
            # Create embed for the message
            embed = discord.Embed(
                description=message_content,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Auto-sent every {interval_str}")
            
            # Create task
            async def send_message():
                while True:
                    try:
                        await channel.send(embed=embed)
                        await asyncio.sleep(interval_seconds)
                    except Exception as e:
                        print(f"Error in autosend task: {e}")
                        break
            
            # Start task
            task = asyncio.create_task(send_message())
            autosend_tasks[channel_id] = task
            
            # Send confirmation
            confirm_embed = discord.Embed(
                title="✅ Autosend Started",
                description=f"Message will be sent to <#{channel_id}> every {interval_str}",
                color=discord.Color.green()
            )
            confirm_embed.add_field(
                name="Message",
                value=message_content,
                inline=False
            )
            await message.channel.send(embed=confirm_embed)
            
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid Interval",
                description="Invalid interval format!\n\nValid formats:\n- m (minutes)\n- h (hours)\n- d (days)",
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
    
    # Handle autosendstop command
    if message.content.startswith('?autosendstop'):
        # Check if user has permission (only specific roles)
        allowed_roles = [1322091136059310100, 1322090684810924033, 1322094447030177863]
        if not any(role.id in allowed_roles for role in message.author.roles):
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
                title="ℹ️ Autosendstop Command Help",
                description="Usage: ?autosendstop <channel_id>",
                color=discord.Color.blue()
            )
            help_embed.add_field(
                name="Example",
                value="?autosendstop 123456789012345678",
                inline=False
            )
            await message.channel.send(embed=help_embed)
            return
        
        try:
            channel_id = int(args[1])
            
            if channel_id in autosend_tasks:
                # Cancel the task
                task = autosend_tasks[channel_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                del autosend_tasks[channel_id]
                
                # Send confirmation
                confirm_embed = discord.Embed(
                    title="✅ Autosend Stopped",
                    description=f"Stopped auto-sending messages to <#{channel_id}>",
                    color=discord.Color.green()
                )
                await message.channel.send(embed=confirm_embed)
            else:
                error_embed = discord.Embed(
                    title="❌ No Active Task",
                    description=f"No active autosend task found for channel <#{channel_id}>",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=error_embed)
                
        except ValueError:
            error_embed = discord.Embed(
                title="❌ Invalid Channel ID",
                description="Please provide a valid channel ID!",
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

client.run(os.getenv('DISCORD_TOKEN'))