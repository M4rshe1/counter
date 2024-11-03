import discord
from discord.ext import commands
import sqlite3
import os
from typing import Optional
from dotenv import load_dotenv
import aiocron

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='Q!', intents=intents)


crontabs = {}

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

def setup_database():
    conn = sqlite3.connect('quantic.db')
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


    c.execute('''CREATE TABLE IF NOT EXISTS advetisement
                 (channel_id INTEGER,
                  server_id INTEGER,
                  message TEXT,
                  interval TEXT,
                  alias TEXT,
                  PRIMARY KEY (channel_id))''')
    conn.commit()
    conn.close()


def setup_crontabs():
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id, interval FROM advetisement WHERE interval IS NOT NULL')
    results = c.fetchall()
    conn.close()

    for channel_id, interval in results:
        crontabs[channel_id] = aiocron.crontab(interval, func=run_advertisement, start=True, args=(channel_id,))

# New helper function to update leaderboard
def update_leaderboard(channel_id: int, user_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('''INSERT INTO leaderboard (channel_id, user_id, count)
                 VALUES (?, ?, 1)
                 ON CONFLICT(channel_id, user_id) DO UPDATE SET
                 count = count + 1''', (channel_id, user_id))
    conn.commit()
    conn.close()

def cron_job(channel_id: int, expression: str):
    job = crontabs.get(channel_id)
    if job:
        job.stop()
    crontabs[channel_id] = aiocron.crontab(expression, func=run_advertisement, start=True, args=(channel_id,))

def delete_cron_job(channel_id: int):
    job = crontabs.get(channel_id)
    if job:
        job.stop()
        del crontabs[channel_id]


async def run_advertisement(channel_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT message FROM advetisement WHERE channel_id = ?', (channel_id,))
    result = c.fetchone()
    conn.close()
    if result:
        channel = bot.get_channel(channel_id)
        message = await channel.send(result[0])
        await message.publish()
    else:
        print('No advertisement message found!')

# New helper function to reset leaderboard
def reset_leaderboard(channel_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM leaderboard WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

# New helper function to get leaderboard
def get_leaderboard(channel_id: int, limit: int = 10) -> list:
    conn = sqlite3.connect('quantic.db')
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
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT current_count, last_user_id, reset_on_wrong FROM counting_channels WHERE channel_id = ?',
              (channel_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None, None)

# Helper function to update channel count
def update_channel_count(channel_id: int, count: int, user_id: int):
    conn = sqlite3.connect('quantic.db')
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
    conn = sqlite3.connect('quantic.db')
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
    setup_crontabs()

@bot.command(name='counting-link')
@has_manage_channels()
async def link_channel(ctx):
    update_channel_count(ctx.channel.id, 0, 0)
    await ctx.send(f'This channel has been set up for counting! Start with 1')

@bot.command(name='advertise-help')
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Advertise Bot Help",
        description="A bot for managing advertisement channels with various features.",
        color=discord.Color.blue()
    )

    admin_commands = """
    `Q!advertise-link <channel_id> <alias>` - Set up current channel for advertisement
    `Q!advertise-unlink <channel_id>` - Unlink current channel from advertisement
    `Q!advertise-message <alias> <message>` - Set advertisement message
    `Q!advertise-interval <alias> <pattern>` - Set advertisement crontab: [Pattern Generator](https://crontab.guru/)
    `Q!advertise-settings` - Show current channel settings
    `Q!advertise <alias>` - Run advertisement for specific alias
    """
    embed.add_field(
        name="👑 Admin Commands (Requires Manage Channels)",
        value=admin_commands,
        inline=False
    )

    embed.set_footer(text="For additional help, contact your server administrators.")
    await ctx.send(embed=embed)


@bot.command(name='h')
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Quantic Bot Help",
        description="A bot for managing counting and advertisement channels with various features.",
        color=discord.Color.blue()
    )

    counting_help = """
    `Q!counting-help` - Show counting bot help
    """
    embed.add_field(
        name="🔢 Counting Bot",
        value=counting_help,
        inline=False
    )

    advertise_help = """
    `Q!advertise-help` - Show advertisement bot help
    """
    embed.add_field(
        name="📢 Advertisement Bot",
        value=advertise_help,
        inline=False
    )


@bot.command(name='advertise-link')
@has_manage_channels()
async def link_advertise_channel(ctx, channel_id: int, alias: str):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    # Check if the alias is already in use for this server
    c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    if c.fetchone():
        await ctx.send('This alias is already in use for this server!')
        return

    c.execute('INSERT OR REPLACE INTO advetisement (channel_id, server_id, alias) VALUES (?, ?, ?)', (channel_id, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="Setup Complete", color=discord.Color.green())
    embed.add_field(name="Channel ID", value=channel_id, inline=True)
    embed.add_field(name="Alias", value=alias, inline=True)
    embed.add_field(name="Set Message command", value="Q!advertise-message <alias> <message>", inline=False)
    embed.add_field(name="Set Interval command", value="Q!advertise-interval <alias> <pattern>", inline=False)
    embed.add_field(name="Unlink command", value="Q!advertise-unlink <channel_id>", inline=False)
    embed.add_field(name="Show Settings command", value="Q!advertise-settings", inline=False)
    embed.add_field(name="Help command", value="Q!advertise-help", inline=False)
    await ctx.send(embed=embed)




@bot.command(name='advertise-unlink')
@has_manage_channels()
async def unlink_advertise_channel(ctx, channel_id: int):
    channel_id = int(channel_id)  # Ensure channel_id is an integer
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM advetisement WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

    delete_cron_job(channel_id)

    await ctx.send('This channel has been unlinked from advertisement!')

@bot.command(name='advertise-message')
@has_manage_channels()
async def set_advertise_message(ctx, alias: str):
    message = ctx.message.content.split(' ', 2)[2]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET message = ? WHERE server_id = ? AND alias = ?', (message, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    await ctx.send('Advertisement message has been set!')

@bot.command(name='advertise')
async def advertise(ctx, alias: str):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()

    if len(alias) == 0:
        await ctx.send('Please provide an alias!')
        return

    c.execute('SELECT message, interval FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        await ctx.send(result[0] if result[0] else 'No message set for this alias!')
    else:
        await ctx.send('This alias is not set up for advertisement!')


@bot.command(name='advertise-interval')
@has_manage_channels()
async def set_advertise_interval(ctx, alias: str):
    interval = ctx.message.content.split(' ', 2)[2]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET interval = ? WHERE server_id = ? AND alias = ?', (interval, ctx.guild.id, alias))
    cron_job(ctx.channel.id, interval)
    conn.commit()
    conn.close()
    await ctx.send('Advertisement interval has been set!')


@bot.command(name='advertise-settings')
@has_manage_channels()
async def show_advertise_settings(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT message, interval, alias FROM advetisement WHERE server_id = ?', (ctx.guild.id,))
    results = c.fetchall()
    conn.close()
    if results:
        embed = discord.Embed(title=f"Channel Settings", color=discord.Color.blue())
        for message, interval, alias in results:
            embed.add_field(name="Advertisement Message", value=("Set" if message else "Not set"), inline=True)
            embed.add_field(name="Advertisement Interval", value=f'`{interval}`', inline=True)
            embed.add_field(name="Alias", value=alias, inline=True)
        await ctx.send(embed=embed)
    if len(results) == 0:
        await ctx.send('This server has no advertisement channels set up!')

@bot.command(name='counting-help')
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Counting Bot Help",
        description="A bot for managing counting channels with various features.",
        color=discord.Color.blue()
    )

    admin_commands = """
    `Q!counting-link` - Set up current channel for counting
    `Q!counting-reset` - Reset count to zero
    `Q!counting-set <number>` - Set count to specific number
    `Q!counting-resetmode <True/False>` - Toggle count reset on wrong numbers
    `Q!counting-settings` - Show current channel settings
    """
    embed.add_field(
        name="👑 Admin Commands (Requires Manage Channels)",
        value=admin_commands,
        inline=False
    )

    user_commands = """
    `Q!counting-leaderboard` or `Q!lb` - Show top counters
    `Q!lb <number>` - Show specific number of top counters (max 25)
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

@bot.command(name='counting-reset')
@has_manage_channels()
async def reset_count(ctx):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_channel_count(ctx.channel.id, 0, 0)
        reset_leaderboard(ctx.channel.id)
        await ctx.send('Count has been reset to 0 and leaderboard has been cleared!')
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='counting-set')
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

@bot.command(name='counting-leaderboard', aliases=['lb'])
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




@bot.command(name='counting-resetmode')
@has_manage_channels()
async def set_reset_mode(ctx, mode: bool):
    current_count, _, current_mode = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_reset_setting(ctx.channel.id, mode)
        mode_str = "will" if mode else "will not"
        await ctx.send(f'Settings updated! Count {mode_str} reset on wrong numbers.')
    else:
        await ctx.send('This channel is not set up for counting!')

@bot.command(name='counting-settings')
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

@bot.command(name='counting-unlink')
@has_manage_channels()
async def unlink_channel(ctx):
    conn = sqlite3.connect('quantic.db')
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
bot.run(TOKEN)