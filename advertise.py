import asyncio
import sqlite3
from datetime import datetime

import aiocron
import discord
import croniter


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
    `/advertise link #channel <alias>` - Set up current channel for advertisement
    `/advertise unlink <alias>` - Unlink channel from advertisement
    `/advertise message <alias> <message>` - Set advertisement message
    `/advertise interval <alias> <pattern>` - Set advertisement crontab: [Pattern Generator](https://crontab.guru/)
    `/advertise settings` - Show current server advertisement settings
    `/advertise send <alias>` - Send advertisement now
    `/advertise image <alias> <image_url>` - Add image to advertisement
    `/advertise <alias>` - Show advertisement message for alias
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
    c.execute('SELECT message, image_url FROM advetisement WHERE channel_id = ?', (channel_id,))
    result = c.fetchone()
    conn.close()
    if result:
        channel = bot.get_channel(channel_id)
        try:
            title = result[0].split('\n')[0]
            body = result[0].split('\n', 1)[1]
            embed = discord.Embed(title=title, color=discord.Color.purple(), description=body)
            if result[1]:
                embed.set_image(url=result[1])
            message = await channel.send(embed=embed)
            await asyncio.sleep(5)
            await message.publish()
            print("Message published successfully.")
        except discord.Forbidden:
            print("Bot lacks permissions to publish the message.")
        except discord.HTTPException as e:
            print(f"An error occurred: {e}")
    else:
        print('No advertisement message found!')

async def show_advertise_settings(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT message, interval, alias, channel_id FROM advetisement WHERE server_id = ?', (ctx.guild.id,))
    results = c.fetchall()
    channel_name = ctx.guild.get_channel(results[0][3]).name if results else None
    conn.close()
    if results:
        for message, interval, alias, channel_id in results:
            embed = discord.Embed(title=f"Channel Settings: {channel_name}", color=discord.Color.blue())
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
        conn.close()
        return

    try:
        cron_job(f"{alias}_{ctx.guild.id}", ctx.message.channel.id, interval, bot)
    except ValueError as e:
        print(e)
        conn.close()
        await ctx.send('Invalid crontab pattern!')
        return
    c.execute('UPDATE advetisement SET interval = ? WHERE server_id = ? AND alias = ?', (interval, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    cron = croniter.croniter(interval)
    next_time = cron.get_next(datetime)
    await ctx.send('Advertisement interval has been set!\nThe next advertisement will be at: ' + str(next_time))

def cron_job(job_id: str, channel_id: int, expression: str, bot):
    job = crontabs.get(job_id)
    if job:
        job.stop()
    crontabs[job_id] = aiocron.crontab(expression, func=run_advertisement, start=True, args=(channel_id, bot))

def delete_cron_job(job_id: str):
    job = crontabs.get(job_id)
    if job:
        job.stop()
        del crontabs[job_id]

async def link_advertise_channel(ctx):

    try:
        mentioned_channel = ctx.message.channel_mentions[0]
        channel_id = mentioned_channel.id
        alias = ctx.message.content.split(' ',3)[3].strip().replace(' ', '_').lower()
    except ValueError:
        await ctx.send('Invalid channel ID!')
        return
    except IndexError:
        await ctx.send('Please provide an alias!')
        return

    if not ctx.guild.get_channel(channel_id):
        await ctx.send('Invalid channel ID!')
        return

    if not ctx.guild.get_channel(channel_id).is_news():
        await ctx.send('This channel is not an announcement channel!')
        return

    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    # Check if the alias is already in use for this server
    c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    if c.fetchone():
        await ctx.send('This alias is already in use for this server!')
        return

    c.execute('INSERT INTO advetisement (channel_id, server_id, alias) VALUES (?, ?, ?)',
              (channel_id, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="Setup Complete", color=discord.Color.green())
    embed.add_field(name="Channel ID", value=channel_id, inline=True)
    embed.add_field(name="Channel Name", value=ctx.guild.get_channel(channel_id).name, inline=True)
    embed.add_field(name="Alias", value=alias, inline=True)
    embed.add_field(name="Set Message command", value="/advertise message <alias> <message>", inline=False)
    embed.add_field(name="Set Interval command", value="/advertise interval <alias> <pattern>", inline=False)
    embed.add_field(name="Unlink command", value="/advertise unlink <alias>", inline=False)
    embed.add_field(name="Show Settings command", value="/advertise settings", inline=False)
    embed.add_field(name="Add Image command", value="/advertise image <alias> <image_url>", inline=False)
    embed.add_field(name="Help command", value="/advertise help", inline=False)
    await ctx.send(embed=embed)

async def unlink_advertise_channel(ctx):
    alias = ctx.message.content.split(' ', 2)[2]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    conn.commit()
    conn.close()

    delete_cron_job(f"{alias}_{ctx.guild.id}")

    await ctx.send('This channel has been unlinked from advertisement!')


async def set_advertise_message(ctx):
    alias = ctx.message.content.split(' ')[2]
    message = ctx.message.content.split(' ', 3)[3]
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

    c.execute('SELECT message, image_url FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        if not result[0]:
            await ctx.send('No message set for this alias!')
            return
        title = result[0].split('\n')[0]
        body = result[0].split('\n', 1)[1]
        embed = discord.Embed(title=title, color=discord.Color.purple(), description=body)
        embed.set_image(url=result[1])
        await ctx.send(embed=embed)
    else:
        await ctx.send('This alias is not set up for advertisement!')


async def advertise_now(ctx, bot):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    alias = ctx.message.content.split(' ')[2]
    c.execute('SELECT channel_id FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        await run_advertisement(result[0], bot)
    else:
        await ctx.send('This alias is not set up for advertisement!')

async def add_image_to_advertisement(ctx):
    alias = ctx.message.content.split(' ')[2]
    image_url = ctx.message.content.split(' ', 3)[3]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET image_url = ? WHERE server_id = ? AND alias = ?', (image_url, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    await ctx.send('Image has been added to advertisement!')


async def advertise_commands(ctx, bot):
    try:
        command = ctx.message.content.split(' ')[1]
    except IndexError:
        command = 'help'

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
    elif command == 'image':
        await add_image_to_advertisement(ctx)
    elif command == 'send':
        await advertise_now(ctx, bot)
    else:
        await advertise(ctx)

