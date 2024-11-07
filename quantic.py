import sqlite3
from datetime import datetime, timedelta
import discord
from ban_button import BanButtons


async def error_set(ctx: discord.Interaction, channel):
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
    await ctx.channel.send(f'Error channel has been set to <#{channel_id}>!')


async def error_remove(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.channel.send('Error channel has not been set!')
        return
    await ctx.channel.send(f"The channel <#{result[0]}> has been removed from being an error channel!")


async def error_list(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.channel.send('No channels have been set!')
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.channel.send('Channels in the database:\n' + '\n'.join(channels))


async def users_add(ctx: discord.Interaction, user):
    user_id = user.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('INSERT INTO allowed_users (user_id, server_id) VALUES (?, ?)', (user_id, ctx.guild.id))
    conn.commit()
    conn.close()
    await ctx.channel.send(f'{user.name} has been added to the database!')

async def users_remove(ctx: discord.Interaction, user):
    user_id = user.id
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    count = c.execute('DELETE FROM allowed_users WHERE user_id = ? AND server_id = ?', (user_id, ctx.guild.id)).rowcount
    conn.commit()
    conn.close()
    if count == 0:
        await ctx.channel.send(f'{user.name} is not in the database!')
        return
    await ctx.channel.send(f'{user.name} has been removed from the database!')

async def users_list(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM allowed_users WHERE server_id = ?', (ctx.guild.id,))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.channel.send('No users have been added to the database!')
        return
    users = [f'<@{result[0]}>' for result in results]
    await ctx.channel.send('Users in the database:\n' + '\n'.join(users))


async def ban_set(ctx: discord.Interaction, channel):
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
    await ctx.channel.send(f'Report channel has been set to <#{channel_id}>!')

async def ban_remove(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.channel.send('Report channel has not been set!')
        return
    await ctx.channel.send(f"The channel <#{result[0]}> has been removed from being a report channel!")

async def ban_list(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.channel.send('No channels have been set!')
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.channel.send('Channels in the database:\n' + '\n'.join(channels))


async def ban_user(ctx: discord.Interaction, user, reason):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    result = c.fetchone()
    if not result:
        await ctx.channel.send('No report channel has been set!')
        return
    report_channel = ctx.guild.get_channel(result[0])
    if not report_channel:
        await ctx.channel.send('Report channel is not found!, Maybe it has been deleted!')
        return
    member = ctx.guild.get_member(user.id)
    if not member:
        await ctx.channel.send('User is not in the server!')
        return
    duration = timedelta(weeks=2)
    try:
        await member.timeout(duration, reason=reason)
    except discord.Forbidden:
        await ctx.channel.send('I do not have permission to timeout this user!')
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
    embed.add_field(name='Reported by', value=f"<@{ctx.user.id}>", inline=False)
    embed.add_field(name='Timout Until', value=f"> {(datetime.now() + duration).strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
    embed.add_field(name='Status', value='Pending', inline=False)
    embed.set_footer(text=f'The Report was created at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    embed.set_thumbnail(url=user.avatar.url)
    await report_channel.send(embed=embed, view=view)


async def quantic_help_command(ctx: discord.Interaction):
    embed = discord.Embed(
        title="📋 Quantic Bot Help",
        description="A bot for managing counting and advertisement channels with various features.",
        color=discord.Color.blue()
    )

    counting_help = """
    `/counting help` - Show counting bot help
    """
    embed.add_field(
        name="🔢 Counting Bot",
        value=counting_help,
        inline=False
    )

    advertise_help = """
    `/advertise help` - Show advertisement bot help
    """
    embed.add_field(
        name="📢 Advertisement Bot",
        value=advertise_help,
        inline=False
    )

    quantic_user_management = """
    `/quantic user add @user` - Add user to allowed users
    `/quantic user remove @user` - Remove user from allowed users
    `/quantic user list` - List allowed users
    """

    embed.add_field(
        name="👤 Quantic User Management",
        value=quantic_user_management,
        inline=False
    )

    quantic_error = """
    `/quantic error set #channel` - Set error channel
    `/quantic error remove` - Remove error channel
    `/quantic error list` - List error channel
    """

    embed.add_field(
        name="🚨 Quantic Error System",
        value=quantic_error,
        inline=False
    )

    quantic_report_system = """
    `/quantic ban @user` - Make a ban report
    `/quantic ban set #channel` - Set ban report channel
    `/quantic ban remove` - Remove ban report channel
    `/quantic ban list` - List ban report channels
    """

    embed.add_field(
        name="🔨 Quantic Report System",
        value=quantic_report_system,
        inline=False
    )

    await ctx.channel.send(embed=embed)

