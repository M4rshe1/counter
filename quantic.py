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
    await ctx.response.send_message(f'Error channel has been set to <#{channel_id}>!', ephemeral=True)


async def error_remove(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.response.send_message('Error channel has not been set!', ephemeral=True)
        return
    await ctx.response.send_message(f"The channel <#{result[0]}> has been removed from being an error channel!", ephemeral=True)


async def error_list(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'ERROR'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.response.send_message('No channels have been set!')
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.response.send_message('Channels in the database:\n' + '\n'.join(channels), ephemeral=True)

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
    await ctx.response.send_message(f'Report channel has been set to <#{channel_id}>!', ephemeral=True)

async def ban_remove(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('DELETE FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT')).fetchone()
    conn.commit()
    conn.close()
    if result.rowcount == 0:
        await ctx.response.send_message('Report channel has not been set!', ephemeral=True)
        return
    await ctx.response.send_message(f"The channel <#{result[0]}> has been removed from being a report channel!", ephemeral=True)

async def ban_list(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    results = c.fetchall()
    conn.close()
    if not results:
        await ctx.response.send_message('No channels have been set!', ephemeral=True)
        return
    channels = [f'<#{result[0]}>' for result in results]
    await ctx.response.send_message('Channels in the database:\n' + '\n'.join(channels))


async def ban_user(ctx: discord.Interaction, user, reason):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM channels WHERE server_id = ? AND type = ?', (ctx.guild.id, 'REPORT'))
    result = c.fetchone()
    if not result:
        await ctx.response.send_message('No report channel has been set!', ephemeral=True)
        return
    report_channel = ctx.guild.get_channel(result[0])
    if not report_channel:
        await ctx.response.send_message('Report channel is not found!, Maybe it has been deleted!', ephemeral=True)
        return
    member = ctx.guild.get_member(user.id)
    if not member:
        await ctx.response.send_message('User is not in the server!', ephemeral=True)
        return
    duration = timedelta(weeks=2)

    # check if user has same or higher role
    if ctx.user.top_role <= member.top_role:
        await ctx.response.send_message('You cannot ban a user with the same or higher role!', ephemeral=True)
        return

    try:
        await member.timeout(duration, reason=reason)
    except discord.Forbidden:
        await ctx.response.send_message('I do not have permission to timeout this user!', ephemeral=True)
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
    embed = discord.Embed(title=f'Ban Report', color=discord.Color.yellow())
    embed.add_field(name='User', value=user_block, inline=False)
    embed.add_field(name='Reason(s)', value=reason_block, inline=False)
    embed.add_field(name='Reported by', value=f"<@{ctx.user.id}>", inline=False)
    embed.add_field(name='Timout Until', value=f"> {(datetime.now() + duration).strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
    embed.add_field(name='Status', value='Pending', inline=False)
    embed.set_footer(text=f'The Report was created at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    embed.set_thumbnail(url=user.avatar.url)
    await report_channel.send(embed=embed, view=view)
    await ctx.response.send_message(f'User has been banned and reported! See <#{report_channel.id}> for more details!', ephemeral=True)


async def quantic_help_command(ctx):
    embed = discord.Embed(
        title="📋 Quantic Bot Help",
        description="Here are the commands you can use with Quantic Bot",
        color=discord.Color.blue()
    )

    counting_help = """
    `/counting link` - Set up current channel for counting
    `/counting set <number>` - Set count to specific number
    `/counting mode <True/False>` - Toggle count reset on wrong numbers
    `/counting settings` - Show current channel settings
    `!lb <?count>` - Show the leaderboard of the current channel
    """

    embed.add_field(
        name="🔢 Counting System",
        value=counting_help,
        inline=False
    )

    advertise_help = """
    `/advertise link #channel <alias>` - Set up current channel for advertisement
    `/advertise unlink <alias>` - Unlink channel from advertisement
    `/advertise settings <alias>` - Set advertisement message
    `/advertise list` - Show current server advertisement settings
    `/advertise send <alias>` - Send advertisement now
    `/advertise get <alias>` - Show advertisement message for alias
    """
    embed.add_field(
        name="📢 Advertisement System",
        value=advertise_help,
        inline=False
    )

    quantic_error = """
    `/error set #channel` - Set error channel
    `/error remove` - Remove error channel
    `/error list` - List error channel
    """

    embed.add_field(
        name="🚨 Quantic Error System",
        value=quantic_error,
        inline=False
    )

    quantic_report_system = """
    `/report user @user <reason>` - Make a ban report
    `/report set #channel` - Set ban report channel
    `/report remove` - Remove ban report channel
    `/report list` - List ban report channels
    """

    embed.add_field(
        name="🔨 Quantic Report System",
        value=quantic_report_system,
        inline=False
    )

    await ctx.send(embed=embed)

