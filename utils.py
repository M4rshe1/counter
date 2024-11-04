import sqlite3
from typing import Optional

def get_channel_info(channel_id: int) -> tuple[Optional[int], Optional[int], Optional[bool]]:
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT current_count, last_user_id, reset_on_wrong FROM counting_channels WHERE channel_id = ?',
              (channel_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, None, None)



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
                  PRIMARY KEY (channel_id, alias))''')

    c.execute('''CREATE TABLE IF NOT EXISTS allowed_users
                    (user_id INTEGER,
                    server_id INTEGER,
                    PRIMARY KEY (user_id, server_id))''')
    conn.commit()
    conn.close()


async def manage_users(ctx):
    command = ctx.message.content.split(' ')[1]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    if command == 'remove':
        user_id = ctx.message.mentions[0].id
        count = c.execute('DELETE FROM allowed_users WHERE user_id = ? AND server_id = ?', (user_id, ctx.guild.id)).rowcount
        conn.commit()
        conn.close()
        if count == 0:
            await ctx.send(f'{ctx.message.mentions[0].name} is not in the database!')
            return
        await ctx.send(f'{ctx.message.mentions[0].name} has been removed from the database!')
        return
    if command == 'add':
        user_id = ctx.message.mentions[0].id
        c.execute('INSERT INTO allowed_users (user_id, server_id) VALUES (?, ?)', (user_id, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(f'{ctx.message.mentions[0].name} has been added to the database!')
    if command == 'list':
        c.execute('SELECT user_id FROM allowed_users WHERE server_id = ?', (ctx.guild.id,))
        results = c.fetchall()
        conn.close()
        if not results:
            await ctx.send('No users have been added to the database!')
            return
        users = [f'<@{result[0]}>' for result in results]
        await ctx.send('Users in the database:\n' + '\n'.join(users))