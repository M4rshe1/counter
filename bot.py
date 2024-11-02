import discord
from discord.ext import commands
import sqlite3
import os
from typing import Optional
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='c!', intents=intents)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

def setup_database():
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS counting_channels
                 (channel_id INTEGER PRIMARY KEY,
                  current_count INTEGER DEFAULT 0,
                  last_user_id INTEGER DEFAULT 0,
                  reset_on_wrong BOOLEAN DEFAULT 1)''')

    # New table for leaderboard
    c.execute('''CREATE TABLE IF NOT EXISTS leaderboard
                 (channel_id INTEGER,
                  user_id INTEGER,
                  count INTEGER DEFAULT 0,
                  PRIMARY KEY (channel_id, user_id))''')
    conn.commit()
    conn.close()

# New helper function to update leaderboard
def update_leaderboard(channel_id: int, user_id: int):
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('''INSERT INTO leaderboard (channel_id, user_id, count)
                 VALUES (?, ?, 1)
                 ON CONFLICT(channel_id, user_id) DO UPDATE SET
                 count = count + 1''', (channel_id, user_id))
    conn.commit()
    conn.close()

# New helper function to reset leaderboard
def reset_leaderboard(channel_id: int):
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('DELETE FROM leaderboard WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

# New helper function to get leaderboard
def get_leaderboard(channel_id: int, limit: int = 10) -> list:
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, count FROM leaderboard 
                 WHERE channel_id = ? 
                 ORDER BY count DESC LIMIT ?''', (channel_id, limit))
    results = c.fetchall()
    conn.close()
    return results

# Permission check
def has_manage_channels():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_channels
    return commands.check(predicate)

# Helper function to get channel info
def get_channel_info(channel_id: int) -> tuple[Optional[int], Optional[int], Optional[bool]]:
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('SELECT current_count, last_user_id, reset_on_wrong FROM counting_channels WHERE channel_id = ?',
              (channel_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None, None)

# Helper function to update channel count
def update_channel_count(channel_id: int, count: int, user_id: int):
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO counting_channels 
                 (channel_id, current_count, last_user_id, reset_on_wrong)
                 VALUES (?, ?, ?, 
                    COALESCE((SELECT reset_on_wrong FROM counting_channels WHERE channel_id = ?), 1))''',
              (channel_id, count, user_id, channel_id))
    conn.commit()
    conn.close()

# Helper function to update reset setting
def update_reset_setting(channel_id: int, reset_on_wrong: bool):
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('''UPDATE counting_channels 
                 SET reset_on_wrong = ?
                 WHERE channel_id = ?''',
              (reset_on_wrong, channel_id))
    conn.commit()
    conn.close()

@bot.event
async def on_ready():
    print(f'Bot is ready: {bot.user.name}')
    setup_database()

@bot.command(name='link')
@has_manage_channels()
async def link_channel(ctx):
    update_channel_count(ctx.channel.id, 0, 0)
    await ctx.send(f'This channel has been set up for counting! Start with 1')

@bot.command(name='chelp')
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Counting Bot Help",
        description="A bot for managing counting channels with various features.",
        color=discord.Color.blue()
    )

    admin_commands = """
    `c!link` - Set up current channel for counting
    `c!reset` - Reset count to zero
    `c!set <number>` - Set count to specific number
    `c!resetmode <True/False>` - Toggle count reset on wrong numbers
    `c!settings` - Show current channel settings
    """
    embed.add_field(
        name="👑 Admin Commands (Requires Manage Channels)",
        value=admin_commands,
        inline=False
    )

    user_commands = """
    `c!leaderboard` or `c!lb` - Show top counters
    `c!lb <number>` - Show specific number of top counters (max 25)
    """
    embed.add_field(
        name="📊 User Commands",
        value=user_commands,
        inline=False
    )

    counting_rules = """
    • Type numbers sequentially (1, 2, 3, etc.)
    • Same person can't count twice in a row
    • Correct numbers get a ✅ reaction
    • Wrong numbers are deleted
    • Count resets on wrong number (if enabled)
    • Leaderboard tracks successful counts
    """
    embed.add_field(
        name="📝 Counting Rules",
        value=counting_rules,
        inline=False
    )

    embed.set_footer(text="For additional help, contact your server administrators.")
    await ctx.send(embed=embed)

@bot.command(name='reset')
@has_manage_channels()
async def reset_count(ctx):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_channel_count(ctx.channel.id, 0, 0)
        reset_leaderboard(ctx.channel.id)
        await ctx.send('Count has been reset to 0 and leaderboard has been cleared!')
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='set')
@has_manage_channels()
async def set_count(ctx, number: int):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_channel_count(ctx.channel.id, number, 0)
        if number == 0:
            reset_leaderboard(ctx.channel.id)
            await ctx.send(f'Count has been set to {number} and leaderboard has been cleared!')
        else:
            await ctx.send(f'Count has been set to {number}!')
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='leaderboard', aliases=['lb'])
async def show_leaderboard(ctx, limit: int = 10):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    if current_count is None:
        await ctx.send('This channel is not set up for counting!')
        return

    leaderboard = get_leaderboard(ctx.channel.id, min(limit, 25))

    if not leaderboard:
        await ctx.send('No entries in the leaderboard yet!')
        return

    embed = discord.Embed(
        title="🏆 Counting Leaderboard",
        description="Top counters in this channel",
        color=discord.Color.gold()
    )

    for index, (user_id, count) in enumerate(leaderboard, 1):
        try:
            user = await bot.fetch_user(user_id)
            username = user.name if user else f"Unknown User ({user_id})"
        except discord.NotFound:
            username = f"Unknown User ({user_id})"
        except discord.HTTPException:
            username = f"Error fetching user ({user_id})"

        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, "👤")
        embed.add_field(
            name=f"{medal} #{index} - {username} ({count})",
            value=f"",
            inline=False
        )

    await ctx.send(embed=embed)




@bot.command(name='resetmode')
@has_manage_channels()
async def set_reset_mode(ctx, mode: bool):
    current_count, _, current_mode = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_reset_setting(ctx.channel.id, mode)
        mode_str = "will" if mode else "will not"
        await ctx.send(f'Settings updated! Count {mode_str} reset on wrong numbers.')
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='settings')
@has_manage_channels()
async def show_settings(ctx):
    current_count, _, reset_mode = get_channel_info(ctx.channel.id)
    if current_count is not None:
        mode_str = "enabled" if reset_mode else "disabled"
        embed = discord.Embed(title="Channel Settings", color=discord.Color.blue())
        embed.add_field(name="Current Count", value=str(current_count), inline=True)
        embed.add_field(name="Reset on Wrong", value=mode_str, inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='unlink')
@has_manage_channels()
async def unlink_channel(ctx):
    conn = sqlite3.connect('counting.db')
    c = conn.cursor()
    c.execute('SELECT * FROM leaderboard WHERE channel_id = ?', (ctx.channel.id,))
    c.execute('DELETE FROM counting_channels WHERE channel_id = ?', (ctx.channel.id,))
    conn.commit()
    conn.close()
    await ctx.send('This channel has been unlinked from counting!')

@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    current_count, last_user_id, reset_on_wrong = get_channel_info(message.channel.id)
    if current_count is None:
        return

    try:
        number = int(message.content)
    except ValueError:
        return

    if number == current_count + 1 and message.author.id != last_user_id:
        update_channel_count(message.channel.id, number, message.author.id)
        update_leaderboard(message.channel.id, message.author.id)
        await message.add_reaction('✅')
    else:
        if message.author.id == last_user_id:
            await message.delete()
            await message.channel.send(
                f"❌ {message.author.mention}, you can't count twice in a row!",
                delete_after=5
            )
        else:
            await message.delete()
            error_msg = f"❌ Wrong number! The count was at {current_count}."
            if reset_on_wrong:
                error_msg += " Starting over!"
                update_channel_count(message.channel.id, 0, 0)
                reset_leaderboard(message.channel.id)
            await message.channel.send(error_msg, delete_after=5)

# Run the bot
bot.run('')