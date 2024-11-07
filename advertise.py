import asyncio
import sqlite3
from datetime import datetime
import aiocron
import discord
import croniter
from discord import ui

from utils import send_error_message

crontabs = {}

def setup_crontabs(client: discord.Client):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id, interval, alias, server_id FROM advetisement WHERE interval IS NOT NULL')
    results = c.fetchall()
    conn.close()


    for channel_id, interval, alias, server_id in results:
        if interval:
            crontabs[f"{alias}_{server_id}"] = aiocron.crontab(interval, func=run_advertisement, start=True, args=(channel_id, client))

async def advertise_help_command(ctx: discord.Interaction):
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
    await ctx.channel.send(embed=embed)


async def run_advertisement(channel_id: int, client: discord.Client):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT message, image_url FROM advetisement WHERE channel_id = ?', (channel_id,))
    result = c.fetchone()
    conn.close()
    if result:
        channel = client.get_channel(channel_id)
        try:
            title = result[0].split('\n')[0]
            body = result[0].split('\n', 1)[1]
            embed = discord.Embed(title=title, color=discord.Color.purple(), description=body)
            if result[1]:
                embed.set_image(url=result[1])
            message = await channel.send(embed=embed)
            await asyncio.sleep(5)
            await message.publish()
        except discord.Forbidden:
            send_error_message(channel_id, "I don't have permission to send messages in this channel!")
        except discord.HTTPException:
            send_error_message(channel_id, "An error occurred while sending the message!")
    else:
        send_error_message(channel_id, "No message set for this alias!")

async def show_advertise_settings(ctx: discord.Interaction):
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
            await ctx.channel.send(embed=embed)
    if len(results) == 0:
        await ctx.channel.send('This server has no advertisement channels set up!')


async def set_advertise_interval(ctx: discord.Interaction, alias, interval):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias)).fetchone()
    if not result:
        await ctx.channel.send('This alias is not set up for advertisement!')
        conn.close()
        return

    try:
        delete_cron_job(f"{alias}_{ctx.guild.id}")
        cron_job(f"{alias}_{ctx.guild.id}", ctx.message.channel.id, interval, ctx)
    except ValueError as e:
        print(e)
        conn.close()
        await ctx.channel.send('Invalid crontab pattern!')
        return
    c.execute('UPDATE advetisement SET interval = ? WHERE server_id = ? AND alias = ?', (interval, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    cron = croniter.croniter(interval)
    next_time = cron.get_next(datetime)
    # calculate the next time the advertisement will run based on the users timezone

    await ctx.channel.send('Advertisement interval has been set!\nThe next advertisement will be at: ' + str(next_time))

def cron_job(job_id: str, channel_id: int, expression: str, ctx: discord.Interaction):
    job = crontabs.get(job_id)
    if job:
        job.stop()
    crontabs[job_id] = aiocron.crontab(expression, func=run_advertisement, start=True, args=(channel_id, ctx.client))

def delete_cron_job(job_id: str):
    job = crontabs.get(job_id)
    if job:
        job.stop()
        del crontabs[job_id]

async def link_advertise_channel(ctx: discord.Interaction, channel, alias):

    if not channel.is_news():
        await ctx.channel.send('This channel is not an announcement channel!')
        return

    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    # Check if the alias is already in use for this server
    c.execute('SELECT * FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    if c.fetchone():
        await ctx.channel.send('This alias is already in use for this server!')
        return

    c.execute('INSERT INTO advetisement (channel_id, server_id, alias) VALUES (?, ?, ?)',
              (channel.id, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    embed = discord.Embed(title="Setup Complete", color=discord.Color.green())
    embed.add_field(name="Channel ID", value=channel.id, inline=True)
    embed.add_field(name="Channel Name", value=channel.name, inline=True)
    embed.add_field(name="Alias", value=alias, inline=True)
    embed.add_field(name="Set Message command", value="/advertise message <alias> <message>", inline=False)
    embed.add_field(name="Set Interval command", value="/advertise interval <alias> <pattern>", inline=False)
    embed.add_field(name="Unlink command", value="/advertise unlink <alias>", inline=False)
    embed.add_field(name="Show Settings command", value="/advertise settings", inline=False)
    embed.add_field(name="Add Image command", value="/advertise image <alias> <image_url>", inline=False)
    embed.add_field(name="Help command", value="/advertise help", inline=False)
    await ctx.channel.send(embed=embed)

async def unlink_advertise_channel(ctx: discord.Interaction, alias):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    conn.commit()
    conn.close()

    delete_cron_job(f"{alias}_{ctx.guild.id}")

    await ctx.channel.send('This channel has been unlinked from advertisement!')


async def set_advertise_message(ctx: discord.Interaction):
    alias = ctx.message.content.split(' ')[2]
    message = ctx.message.content.split(' ', 3)[3]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET message = ? WHERE server_id = ? AND alias = ?', (message, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    await ctx.channel.send('Advertisement message has been set!')


async def advertise(ctx: discord.Interaction, alias):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()

    c.execute('SELECT message, image_url FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        if not result[0]:
            await ctx.channel.send('No message set for this alias!')
            return
        title = result[0].split('\n')[0]
        body = result[0].split('\n', 1)[1]
        embed = discord.Embed(title=title, color=discord.Color.purple(), description=body)
        embed.set_image(url=result[1])
        await ctx.channel.send(embed=embed)
    else:
        await ctx.channel.send('This alias is not set up for advertisement!')


async def advertise_now(ctx: discord.Interaction, alias):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM advetisement WHERE server_id = ? AND alias = ?', (ctx.guild.id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        await run_advertisement(result[0], ctx.client)
    else:
        await ctx.channel.send('This alias is not set up for advertisement!')

async def add_image_to_advertisement(ctx: discord.Interaction, alias, image_url):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('UPDATE advetisement SET image_url = ? WHERE server_id = ? AND alias = ?', (image_url, ctx.guild.id, alias))
    conn.commit()
    conn.close()
    await ctx.channel.send('Image has been added to advertisement!')

from discord import ui

class AdvertisementSetupModal(ui.Modal, title="Set Advertisement Details"):
    def __init__(self, alias, client, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias = alias
        self.client = client

        # Connect to the database and get current values for the alias
        conn = sqlite3.connect('quantic.db')
        c = conn.cursor()
        c.execute('SELECT message, image_url, interval FROM advetisement WHERE alias = ?', (alias,))
        result = c.fetchone()
        conn.close()

        # Pre-fill the fields if there are values in the database
        message_text = result[0] if result and result[0] else ""
        image_url_text = result[1] if result and result[1] else ""
        interval_text = result[2] if result and result[2] else ""

        # Updated to use TextInput instead of InputText
        self.add_item(ui.TextInput(label="Message", style=discord.TextStyle.long, default=message_text, required=False))
        self.add_item(ui.TextInput(label="Image URL", style=discord.TextStyle.short, default=image_url_text, required=False, placeholder="https://example.com/image.jpg"))
        self.add_item(ui.TextInput(label="Interval (Cron format -> crontab.guru)", style=discord.TextStyle.short, default=interval_text, required=False, placeholder="* * * * *"))

    async def callback(self, interaction: discord.Interaction):
        message_input = next(item for item in self.children if isinstance(item, ui.TextInput) and item.label == "Message")
        image_url_input = next(item for item in self.children if isinstance(item, ui.TextInput) and item.label == "Image URL")
        interval_input = next(item for item in self.children if isinstance(item, ui.TextInput) and item.label == "Interval (Cron format)")

        message = message_input.value
        image_url = image_url_input.value
        interval = interval_input.value

        conn = sqlite3.connect('quantic.db')
        c = conn.cursor()
        c.execute('UPDATE advetisement SET message = ?, image_url = ?, interval = ? WHERE alias = ? AND server_id = ?',
                  (message, image_url, interval, self.alias, interaction.guild.id))
        conn.commit()
        conn.close()
        await interaction.channel.send("Advertisement details updated successfully!")

        if interval:
            # Ensure cron jobs are cleared and scheduled properly
            delete_cron_job(f"{self.alias}_{interaction.guild.id}")
            cron_job(f"{self.alias}_{interaction.guild.id}", interaction.channel.id, interval, interaction)
