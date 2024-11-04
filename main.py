import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from advertise import advertise_commands, setup_crontabs
from counting import counting_commands, counting_chat_evaluation, show_leaderboard
from utils import setup_database

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

@bot.hybrid_command()
async def hello(ctx):
    await ctx.send("Hello!")

@bot.hybrid_command()
async def sync(ctx):
    await ctx.message.delete()
    message = await ctx.send("Syncing...")
    await bot.tree.sync(guild=ctx.guild)
    await message.edit(content="Synced!", delete_after=5)

# Permission check
def has_manage_channels():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_channels

    return commands.check(predicate)

def channel_is_in_guild(channel_id):
    async def predicate(ctx):
        return ctx.guild.get_channel(channel_id) is not None

    return commands.check(predicate)


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

    await ctx.send(embed=embed)


@bot.hybrid_command(name='counting')
@has_manage_channels()
async def counting(ctx):
    return await counting_commands(ctx, bot)


@bot.hybrid_command(name='advertise')
@has_manage_channels()
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