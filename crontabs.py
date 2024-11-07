import asyncio
import sqlite3

import aiocron
import discord
from utils import send_error_message

crontabs = {}


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

def setup_crontabs(client: discord.Client):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id, interval, alias, server_id FROM advetisement WHERE interval IS NOT NULL')
    results = c.fetchall()
    conn.close()

    for channel_id, interval, alias, server_id in results:
        if interval:
            crontabs[f"{alias}_{server_id}"] = aiocron.crontab(interval, func=run_advertisement, start=True,
                                                               args=(channel_id, client))


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
