import sqlite3

import discord
from utils import get_channel_info

def update_channel_count(channel_id: int, count: int, user_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO counting_channels 
                 (channel_id, current_count, last_user_id, reset_on_wrong)
                 VALUES (?, ?, ?, 
                    COALESCE((SELECT reset_on_wrong FROM counting_channels WHERE channel_id = ?), 1))''',
              (channel_id, count, user_id, channel_id))
    conn.commit()
    conn.close()

async def counting_unlink_channel(ctx: discord.Interaction):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('SELECT * FROM leaderboard WHERE channel_id = ?', (ctx.channel.id,))
    c.execute('DELETE FROM counting_channels WHERE channel_id = ?', (ctx.channel.id,))
    conn.commit()
    conn.close()
    await ctx.response.send_message('This channel has been unlinked from counting!', ephemeral=True)

async def counting_show_settings(ctx: discord.Interaction):
    current_count, _, reset_mode = get_channel_info(ctx.channel.id)
    if current_count is not None:
        mode_str = "enabled" if reset_mode else "disabled"
        embed = discord.Embed(title="Channel Settings", color=discord.Color.blue())
        embed.add_field(name="Current Count", value=str(current_count), inline=True)
        embed.add_field(name="Reset on Wrong", value=mode_str, inline=True)
        await ctx.response.send_message(embed=embed)
    else:
        await ctx.response.send_message('This channel is not set up for counting!', ephemeral=True)


async def counting_link_channel(ctx: discord.Interaction):
    update_channel_count(ctx.channel.id, 0, 0)
    await ctx.response.send_message(f'This channel has been set up for counting! Start with 1', ephemeral=True)

# Helper function to update reset setting
def update_reset_setting(ctx: discord.Interaction, reset_on_wrong: bool):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('''UPDATE counting_channels 
                 SET reset_on_wrong = ?
                 WHERE channel_id = ?''',
              (reset_on_wrong, ctx.channel.id))
    conn.commit()
    conn.close()

# New helper function to reset leaderboard
def reset_leaderboard(channel_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('DELETE FROM leaderboard WHERE channel_id = ?', (channel_id,))
    conn.commit()
    conn.close()

# New helper function to get leaderboard
def get_leaderboard(channel_id: int, limit: int = 10) -> list:
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, count FROM leaderboard 
                 WHERE channel_id = ? 
                 ORDER BY count DESC LIMIT ?''', (channel_id, limit))
    results = c.fetchall()
    conn.close()
    return results

# New helper function to update leaderboard
def update_leaderboard(channel_id: int, user_id: int):
    conn = sqlite3.connect('quantic.db')
    c = conn.cursor()
    result = c.execute('SELECT count FROM leaderboard WHERE channel_id = ? AND user_id = ?', (channel_id, user_id)).fetchone()
    if result:
        c.execute('UPDATE leaderboard SET count = count + 1 WHERE channel_id = ? AND user_id = ?', (channel_id, user_id))
    else:
        c.execute('''INSERT INTO leaderboard (channel_id, user_id, count)
                 VALUES (?, ?, 1)
                 ON CONFLICT(channel_id, user_id) DO UPDATE SET
                 count = count + 1''', (channel_id, user_id))
    conn.commit()
    conn.close()

async def counting_set_count(ctx: discord.Interaction, number: int):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_channel_count(ctx.channel.id, number, 0)
        if number == 0:
            reset_leaderboard(ctx.channel.id)
            await ctx.response.send_message(f'Count has been set to {number} and leaderboard has been cleared!', ephemeral=True)
        else:
            await ctx.response.send_message(f'Count has been set to {number}!', ephemeral=True)
    else:
        await ctx.response.send_message('This channel is not set up for counting!', ephemeral=True)


async def show_leaderboard(ctx, limit: int = 10):
    current_count, _, _ = get_channel_info(ctx.channel.id)
    await ctx.message.delete()
    if current_count is None:
        await ctx.send('This channel is not set up for counting!', ephemeral=True)
        return

    leaderboard = get_leaderboard(ctx.channel.id, min(limit, 25))

    if not leaderboard:
        await ctx.send('No entries in the leaderboard yet!', ephemeral=True)
        return

    embed = discord.Embed(
        title="🏆 Counting Leaderboard",
        description="Top counters in this channel",
        color=discord.Color.gold()
    )

    for index, (user_id, count) in enumerate(leaderboard, 1):
        try:
            user = await ctx.guild.fetch_member(user_id)
            username = user.name if user else f"Unknown User ({user_id})"
        except discord.NotFound:
            username = f"Unknown User ({user_id})"
        except discord.HTTPException:
            username = f"Error fetching user ({user_id})"

        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, "👤")
        embed.add_field(
            name=f"{medal} #{index} - {username} ({count})",
            value=f"",
            inline=False
        )

    await ctx.send(embed=embed, ephemeral=True)

async def set_reset_mode(ctx: discord.Interaction):
    mode = ctx.message.content.split(' ')[2].lower()
    if mode == 'true':
        mode = True
    elif mode == 'false':
        mode = False
    current_count, _, current_mode = get_channel_info(ctx.channel.id)
    if current_count is not None:
        update_reset_setting(ctx.channel.id, mode)
        mode_str = "will" if mode else "will not"
        await ctx.response.send_message(f'Settings updated! Count {mode_str} reset on wrong numbers.', ephemeral=True)
    else:
        await ctx.response.send_message('This channel is not set up for counting!', ephemeral=True)

async def counting_chat_evaluation(message: discord.Message):
    current_count, last_user_id, reset_on_wrong = get_channel_info(message.channel.id)
    if current_count is None:
        return
    try:
        number = int(message.content)
    except ValueError:
        await message.channel.send("❌ Only numbers are allowed in this channel!", delete_after=5)
        await message.delete()
        return

    if number == current_count + 1 and message.author.id != last_user_id:
        await message.add_reaction('✅')
        update_channel_count(message.channel.id, number, message.author.id)
        update_leaderboard(message.channel.id, message.author.id)
    elif message.author.id == last_user_id:
        await message.delete()
        await message.channel.send(
                f"❌ {message.author.mention}, you can't count twice in a row!",
                delete_after=5
        )
    else:
        await message.delete()
        error_msg = f"❌ Wrong number! The count was at {current_count}."
        if reset_on_wrong:
            error_msg += " Starting over!"
            update_channel_count(message.channel.id, 0, 0)
            reset_leaderboard(message.channel.id)
        await message.channel.send(error_msg, delete_after=5)


