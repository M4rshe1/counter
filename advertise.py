import sqlite3
import aiocron
import discord


crontabs = {}

def setup_crontabs(bot):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id, interval FROM advetisement WHERE interval IS NOT NULL')
    results = c.fetchall()
    conn.close()

    for channel_id, interval in results:
        crontabs[channel_id] = aiocron.crontab(interval, func=run_advertisement, start=True, args=(channel_id, bot))

async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Advertise Bot Help",
        description="A bot for managing advertisement channels with various features.",
        color=discord.Color.blue()
    )

    admin_commands = """
    `Q!advertise link- <channel_id> <alias>` - Set up current channel for advertisement
    `Q!advertise unlink <channel_id>` - Unlink current channel from advertisement
    `Q!advertise message <alias> <message>` - Set advertisement message
    `Q!advertise interval <alias> <pattern>` - Set advertisement crontab: [Pattern Generator](https://crontab.guru/)
    `Q!advertise settings` - Show current server advertisement settings
    `Q!advertise <alias>` - Show advertisement message for alias
    """
    embed.add_field(
        name="👑 Admin Commands (Requires Manage Channels)",
        value=admin_commands,
        inline=False
    )

    embed.set_footer(text="For additional help, contact your server administrators.")
    await ctx.send(embed=embed)


async def run_advertisement(channel_id: int, bot):
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


async def set_advertise_interval(ctx, bot):
    alias = ctx.message.content.split(' ')[2]
    interval = ctx.message.content.split(' ', 3)[3]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias)).fetchone()
    if not result:
        await ctx.send('This alias is not set up for advertisement!')
        return
    c.execute('UPDATE advetisement SET interval = ? WHERE server_id = ? AND alias = ?', (interval, ctx.guild.id, alias))
    cron_job(ctx.channel.id, interval, bot)
    conn.commit()
    conn.close()
    await ctx.send('Advertisement interval has been set!')

def cron_job(channel_id: int, expression: str, bot):
    job = crontabs.get(channel_id)
    if job:
        job.stop()
    crontabs[channel_id] = aiocron.crontab(expression, func=run_advertisement, start=True, args=(channel_id, bot))

def delete_cron_job(channel_id: int):
    job = crontabs.get(channel_id)
    if job:
        job.stop()
        del crontabs[channel_id]

async def link_advertise_channel(ctx):
    channel_id = int(ctx.message.content.split(' ')[2])
    alias = ctx.message.content.split(' ')[3]

    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    # Check if the alias is already in use for this server
    c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    if c.fetchone():
        await ctx.send('This alias is already in use for this server!')
        return

    c.execute('INSERT OR REPLACE INTO advertisement (channel_id, server_id, alias) VALUES (?, ?, ?)',
              (channel_id, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="Setup Complete", color=discord.Color.green())
    embed.add_field(name="Channel ID", value=channel_id, inline=True)
    embed.add_field(name="Alias", value=alias, inline=True)
    embed.add_field(name="Set Message command", value="Q!advertise message <alias> <message>", inline=False)
    embed.add_field(name="Set Interval command", value="Q!advertise interval <alias> <pattern>", inline=False)
    embed.add_field(name="Unlink command", value="Q!advertise unlink <channel_id>", inline=False)
    embed.add_field(name="Show Settings command", value="Q!advertise settings", inline=False)
    embed.add_field(name="Help command", value="Q!advertise-help", inline=False)
    await ctx.send(embed=embed)

async def unlink_advertise_channel(ctx):
    channel_id = ctx.message.content.split(' ')[2]
    channel_id = int(channel_id)  # Ensure channel_id is an integer
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM advetisement WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

    delete_cron_job(channel_id)

    await ctx.send('This channel has been unlinked from advertisement!')


async def set_advertise_message(ctx):
    alias = ctx.message.content.split(' ')[2]
    message = ctx.message.content.split(' ', 3)[3]
    print(alias, message)
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET message = ? WHERE server_id = ? AND alias = ?', (message, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    await ctx.send('Advertisement message has been set!')


async def advertise(ctx):
    alias = ctx.message.content.split(' ')[1]
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


async def advertise_commands(ctx, bot):
    command = ctx.message.content.split(' ')[1]
    if command == 'help':
        await help_command(ctx)
    elif command == 'link':
        await link_advertise_channel(ctx)
    elif command == 'unlink':
        await unlink_advertise_channel(ctx)
    elif command == 'message':
        await set_advertise_message(ctx)
    elif command == 'interval':
        await set_advertise_interval(ctx, bot)
    elif command == 'settings':
        await show_advertise_settings(ctx)
    else:
        await advertise(ctx)

