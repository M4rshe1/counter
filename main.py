import os
import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from advertise import advertise_commands, setup_crontabs
from counting import counting_commands, counting_chat_evaluation, show_leaderboard
from utils import setup_database
from quantic import error_set, error_remove, users_add, users_remove, users_list
from BanButtons import BanButtons

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

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

class SlashCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.setup_group_commands())

    class QuanticGroup(app_commands.Group, name="quantic", description="Quantic bot administration"):
        class ErrorGroup(app_commands.Group, name="error"):
            @app_commands.command(name="set", description="Set error channel")
            async def set(self, interaction: discord.Interaction, channel: discord.TextChannel):
                await error_set(interaction, channel)

            @app_commands.command(name="remove", description="Remove error channel")
            async def remove(self, interaction: discord.Interaction):
                await error_remove(interaction)

            @app_commands.command(name="list", description="List error channels")
            async def list(self, interaction: discord.Interaction):
                await interaction.channel.send("Error channel list commands")


        class UserGroup(app_commands.Group, name="user"):
            @app_commands.command(name="add", description="Add user to allowed users")
            async def add(self, interaction: discord.Interaction, user: discord.User):
                await users_add(interaction, user)

            @app_commands.command(name="remove", description="Remove user from allowed users")
            async def remove(self, interaction: discord.Interaction, user: discord.User):
                await users_remove(interaction, user)

            @app_commands.command(name="list", description="List allowed users")
            async def list(self, interaction: discord.Interaction):
                await users_list(interaction)

        class BanGroup(app_commands.Group, name="ban"):
            @app_commands.command(name="set", description="Set ban report channel")
            async def set(self, interaction: discord.Interaction, channel: discord.TextChannel):
                await interaction.channel.send("Ban report set commands")

            @app_commands.command(name="remove", description="Remove ban report channel")
            async def remove(self, interaction: discord.Interaction):
                await interaction.channel.send("Ban report remove commands")

            @app_commands.command(name="list", description="List ban report channels")
            async def list(self, interaction: discord.Interaction):
                await interaction.channel.send("Ban report list commands")

            @app_commands.command(name="ban", description="Ban a user from the server")
            async def ban(self, interaction: discord.Interaction, user: discord.User):
                print("Ban user")
                await interaction.channel.send(f"Ban user {user.name}")


        def __init__(self):
            super().__init__()
            self.add_command(self.UserGroup())
            self.add_command(self.BanGroup())
            self.add_command(self.ErrorGroup())

    async def setup_group_commands(self):
        self.bot.tree.add_command(self.QuanticGroup())
        await self.bot.tree.sync()

    @commands.command()
    async def h(self, interaction: discord.Interaction):
        await help_command(interaction)

    @commands.command()
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send("Commands synced!")

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    # Add the SlashCommands cog after the bot is ready
    setup_database()
    setup_crontabs(client)
    client.add_view(BanButtons())
    await client.add_cog(SlashCommands(client))



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')









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

    await ctx.channel.send(embed=embed)


# @bot.hybrid_command(name='counting')
# @is_allowed()
# async def counting(ctx):
#     return await counting_commands(ctx, bot)
#
#
# @bot.hybrid_command(name='advertise')
# @is_allowed()
# async def advertise(ctx):
#     return await advertise_commands(ctx, bot)
#
# @bot.hybrid_command(name='lb')
# async def leaderboard(ctx):
#     await show_leaderboard(ctx, bot)



@client.event
async def on_message(message):
    await client.process_commands(message)

    if message.author.bot:
        return

    if message.content.startswith('/'):
        return

    await counting_chat_evaluation(message)





client.run(TOKEN)