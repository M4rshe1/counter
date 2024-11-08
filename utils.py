import sqlite3
from typing import Optional

import discord


def get_channel_info(channel_id: int) -> tuple[Optional[int], Optional[int], Optional[bool]]:
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT current_count, last_user_id, reset_on_wrong FROM counting_channels WHERE channel_id = ?',
              (channel_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None, None)

def send_error_message(ctx: discord.Interaction, message: str):
    print('Error:', message)
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR'))
    result = c.fetchone()
    conn.close()
    if not result:
        return
    error_channel = ctx.guild.get_channel(result[0])
    if not error_channel:
        return
    error_message = f'Error in <#{ctx.channel.id}>: {message}'
    error_channel.send(error_message)


def setup_database():
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS counting_channels
                 (channel_id INTEGER PRIMARY KEY,
                  current_count INTEGER DEFAULT 0,
                  last_user_id INTEGER DEFAULT 0,
                  reset_on_wrong BOOLEAN DEFAULT 0)''')

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
                  image_url TEXT,
                  PRIMARY KEY (channel_id, alias))''')

    c.execute('''CREATE TABLE IF NOT EXISTS channels
                 (server_id INTEGER,
                  channel_id INTEGER,
                  type TEXT,
                  PRIMARY KEY (type, channel_id))''')
    conn.commit()
    conn.close()

