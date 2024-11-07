import sqlite3
from datetime import datetime, timedelta

import discord

from BanButtons import BanButtons


async def error_set(ctx, channel):
    channel_id = channel.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    existing = c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR')).fetchone()
    if existing:
        c.execute('UPDATE channels SET channel_id = ? WHERE server_id = ? AND type = ?', (channel_id, ctx.guild.id, 'ERROR'))
    else:
        c.execute('INSERT INTO channels (server_id, channel_id, type) VALUES (?, ?, ?)', (ctx.guild.id, channel_id, 'ERROR'))
    conn.commit()
    conn.close()
    await ctx.send(f'Error channel has been set to <#{channel_id}>!')


async def error_remove(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.send('Error channel has not been set!')
        return
    await ctx.send(f"The channel <#{result[0]}> has been removed from being an error channel!")


async def error_list(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.send('No channels have been set!')
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.send('Channels in the database:\n' + '\n'.join(channels))


async def error_commands(ctx):
    command = ctx.message.content.split(' ')[2]
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    if command == 'set':
        await error_set(ctx, ctx.message.channel_mentions[0])
    if command == 'remove':
        await error_remove(ctx)
    if command == 'list':
        await error_list(ctx)


async def users_add(ctx, user):
    user_id = user.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('INSERT INTO allowed_users (user_id, server_id) VALUES (?, ?)', (user_id, ctx.guild.id))
    conn.commit()
    conn.close()
    await ctx.send(f'{user.name} has been added to the database!')

async def users_remove(ctx, user):
    user_id = user.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    count = c.execute('DELETE FROM allowed_users WHERE user_id = ? AND server_id = ?', (user_id, ctx.guild.id)).rowcount
    conn.commit()
    conn.close()
    if count == 0:
        await ctx.send(f'{user.name} is not in the database!')
        return
    await ctx.send(f'{user.name} has been removed from the database!')

async def users_list(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM allowed_users WHERE server_id = ?', (ctx.guild.id,))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.send('No users have been added to the database!')
        return
    users = [f'<@{result[0]}>' for result in results]
    await ctx.send('Users in the database:\n' + '\n'.join(users))

async def users_commands(ctx):
    command = ctx.message.content.split(' ')[2]
    if command == 'remove':
        await users_remove(ctx, ctx.message.mentions[0])
    elif command == 'add':
        await users_add(ctx, ctx.message.mentions[0])
    elif command == 'list':
        await users_list(ctx)


async def ban_set(ctx, channel):
    channel_id = channel.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    existing = c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT')).fetchone()
    if existing:
        c.execute('UPDATE channels SET channel_id = ? WHERE server_id = ? AND type = ?', (channel_id, ctx.guild.id, 'REPORT'))
    else:
        c.execute('INSERT INTO channels (server_id, channel_id, type) VALUES (?, ?, ?)', (ctx.guild.id, channel_id, 'REPORT'))
    conn.commit()
    conn.close()
    await ctx.send(f'Report channel has been set to <#{channel_id}>!')

async def ban_remove(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.send('Report channel has not been set!')
        return
    await ctx.send(f"The channel <#{result[0]}> has been removed from being a report channel!")

async def ban_list(ctx):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.send('No channels have been set!')
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.send('Channels in the database:\n' + '\n'.join(channels))


async def ban_user(ctx, user, reason):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    result = c.fetchone()
    if not result:
        await ctx.send('No report channel has been set!')
        return
    report_channel = ctx.guild.get_channel(result[0])
    if not report_channel:
        await ctx.send('Report channel is not found!, Maybe it has been deleted!')
        return
    member = ctx.guild.get_member(user.id)
    if not member:
        await ctx.send('User is not in the server!')
        return
    duration = timedelta(weeks=2)
    try:
        await member.timeout(duration, reason=reason)
    except discord.Forbidden:
        await ctx.send('I do not have permission to ban this user!')
        return
    view = BanButtons()
    user_block = f'''
    > User: `@{user.name}` (<@{user.id}>)
    > ID: `{user.id}`
    > Joined: `{user.joined_at.strftime('%Y-%m-%d %H:%M:%S')}`
    '''

    reason_block = f'''
    > {reason}
    '''
    embed = discord.Embed(title='User Ban Report', color=discord.Color.yellow())
    embed.add_field(name='User', value=user_block, inline=False)
    embed.add_field(name='Reason(s)', value=reason_block, inline=False)
    embed.add_field(name='Reported by', value=f"<@{ctx.author.id}>", inline=False)
    embed.add_field(name='Timout Until', value=f"> {(datetime.now() + duration).strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
    embed.add_field(name='Status', value='Pending', inline=False)
    embed.set_footer(text=f'The Report was created at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    embed.set_thumbnail(url=user.avatar.url)
    await report_channel.send(embed=embed, view=view)

async def ban_commands(ctx):
    command = ctx.message.content.split(' ')[2]
    conn = sqlite3.connect('quantic.db')
    try:
        user = ctx.message.mentions[0]
    except IndexError:
        user = None
        pass
    c = conn.cursor()
    if user is not None:
        reason = ctx.message.content.split(' ',3)[3]
        await ban_user(ctx, user, reason)


    elif command == 'set':
        await ban_set(ctx, ctx.message.channel_mentions[0])

    elif command == 'remove':
        await ban_remove(ctx)

    elif command == 'list':
        await ban_list(ctx)



async def quantic_commands(ctx):
    command = ctx.message.content.split(' ')[1]
    if command == 'error':
        await error_commands(ctx)
    if command == 'users':
        await users_commands(ctx)
    if command == 'ban':
        await ban_commands(ctx)


