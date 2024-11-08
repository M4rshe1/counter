import asyncio
import sqlite3

import aiocron
import discord
from utils import send_error_message

crontabs = {}


def cron_job(job_id: str, ctx: discord.Interaction, expression: str, alias: str):
    job = crontabs.get(job_id)
    if job:
        job.stop()
    crontabs[job_id] = aiocron.crontab(expression, func=run_advertisement, start=True, args=(alias, ctx.guild.id, ctx.client))


def delete_cron_job(job_id: str):
    job = crontabs.get(job_id)
    if job:
        job.stop()
        del crontabs[job_id]


def setup_crontabs(client: discord.Client):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id, interval, alias, server_id FROM advetisement WHERE interval IS NOT NULL')
    results = c.fetchall()
    conn.close()

    for channel_id, interval, alias, server_id in results:
        if interval:
            crontabs[f"{alias}_{server_id}"] = aiocron.crontab(interval, func=run_advertisement, start=True,
                                                               args=(alias, server_id, client))


async def run_advertisement(alias: str, server_id, client: discord.Client):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT message, image_url, channel_id FROM advetisement WHERE server_id = ? AND alias = ?', (server_id, alias))
    result = c.fetchone()
    conn.close()
    if result:
        channel = client.get_channel(result[2])
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
            send_error_message(ctx, "I don't have permission to send messages in this channel!")
        except discord.HTTPException:
            send_error_message(ctx, "An error occurred while sending the message!")
    else:
        send_error_message(ctx, "No message set for this alias!")
