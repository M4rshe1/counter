import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

from advertise import advertise_commands, setup_crontabs
from counting import counting_commands, counting_chat_evaluation
from utils import setup_database

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix=['Q!', 'q!'], intents=intents)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')




# Permission check
def has_manage_channels():
    async def predicate(ctx):
        return ctx.author.guild_permissions.manage_channels

    return commands.check(predicate)


@bot.event
async def on_ready():
    print(f'Bot is ready: {bot.user.name}')
    setup_database()
    setup_crontabs(bot)


@bot.command(name='h', aliases=['?'])
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 Quantic Bot Help",
        description="A bot for managing counting and advertisement channels with various features.",
        color=discord.Color.blue()
    )

    counting_help = """
    `Q!counting help` - Show counting bot help
    """
    embed.add_field(
        name="🔢 Counting Bot",
        value=counting_help,
        inline=False
    )

    advertise_help = """
    `Q!advertise help` - Show advertisement bot help
    """
    embed.add_field(
        name="📢 Advertisement Bot",
        value=advertise_help,
        inline=False
    )

    ctx.send(embed=embed)


@bot.command(name='counting')
@has_manage_channels()
async def counting(ctx):
    return await counting_commands(ctx, bot)


@bot.command(name='advertise')
@has_manage_channels()
async def advertise(ctx):
    return await advertise_commands(ctx, bot)


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if message.author.bot:
        return

    if message.content.startswith('Q!'):
        return

    await counting_chat_evaluation(message)


# Run the bot
bot.run(TOKEN)
