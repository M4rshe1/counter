import os
import sqlite3

import discord
from discord.ext import commands
from dotenv import load_dotenv

from advertise import advertise_commands, setup_crontabs
from counting import counting_commands, counting_chat_evaluation, show_leaderboard
from utils import setup_database
from quantic import quantic_commands

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        # await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        setup_database()
        setup_crontabs(self)
        print('Setup complete!')

bot = MyBot()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')



# Permission check
def is_allowed():
    async def predicate(ctx):
        conn = sqlite3.connect('quantic.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM allowed_users WHERE user_id = ? AND server_id = ?', (ctx.author.id, ctx.guild.id))
        result = c.fetchone()
        conn.close()
        if result:
            return True
        else:
            return ctx.author.guild_permissions.manage_channels



    return commands.check(predicate)

def channel_is_in_guild(channel_id):
    async def predicate(ctx):
        return ctx.guild.get_channel(channel_id) is not None

    return commands.check(predicate)


@bot.hybrid_command(name='quantic')
@is_allowed()
async def quantic(ctx):
    await quantic_commands(ctx)

@bot.hybrid_command()
@is_allowed()
async def sync(ctx):
    await ctx.message.delete()
    message = await ctx.send("Syncing...")
    await bot.tree.sync(guild=ctx.guild)
    await message.edit(content="Synced!", delete_after=5)

@bot.hybrid_command(name='h')
async def help_command(ctx):
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

    await ctx.send(embed=embed)


@bot.hybrid_command(name='counting')
@is_allowed()
async def counting(ctx):
    return await counting_commands(ctx, bot)


@bot.hybrid_command(name='advertise')
@is_allowed()
async def advertise(ctx):
    return await advertise_commands(ctx, bot)

@bot.hybrid_command(name='lb')
async def leaderboard(ctx):
    await show_leaderboard(ctx, bot)


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if message.content.startswith('/'):
        return

    await counting_chat_evaluation(message)



bot.run(TOKEN)