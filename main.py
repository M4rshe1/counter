import os
import sqlite3
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from advertise import  advertise_help_command, link_advertise_channel, \
    unlink_advertise_channel, show_advertise_settings, advertise, advertise_now, advertisement_settings
from counting import counting_chat_evaluation, show_leaderboard, counting_help_command, \
    counting_link_channel, update_reset_setting, counting_set_count, counting_show_settings, counting_unlink_channel
from crontabs import setup_crontabs
from utils import setup_database
from quantic import error_set, error_remove, users_add, users_remove, users_list, ban_user, ban_set, ban_remove, \
    ban_list, quantic_help_command, error_list
from ban_button import BanButtons

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


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
                await error_list(interaction)


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

        class ReportGroup(app_commands.Group, name="report"):
            @app_commands.command(name="set", description="Set ban report channel")
            async def set(self, interaction: discord.Interaction, channel: discord.TextChannel):
                await ban_set(interaction, channel)

            @app_commands.command(name="remove", description="Remove ban report channel")
            async def remove(self, interaction: discord.Interaction):
                await ban_remove(interaction)

            @app_commands.command(name="list", description="List ban report channels")
            async def list(self, interaction: discord.Interaction):
                await ban_list(interaction)

        @app_commands.command(name="ban", description="Make a ban report")
        async def report(self, interaction: discord.Interaction, user: discord.User, reason: str):
            await ban_user(interaction, user, reason)


        def __init__(self):
            super().__init__()
            self.add_command(self.UserGroup())
            self.add_command(self.ReportGroup())
            self.add_command(self.ErrorGroup())

    class CountingGroup(app_commands.Group, name="counting", description="Counting bot commands"):
        @app_commands.command(name="help", description="Show counting bot help")
        async def help(self, interaction: discord.Interaction):
            await counting_help_command(interaction)

        @app_commands.command(name="leaderboard", description="Show top counters")
        async def leaderboard(self, interaction: discord.Interaction, count: Optional[int] = 10):
            await show_leaderboard(interaction, count)

        @app_commands.command(name="link", description="Set up current channel for counting")
        async def link(self, interaction: discord.Interaction):
            await counting_link_channel(interaction)

        @app_commands.command(name="mode", description="Toggle count reset on wrong numbers")
        async def mode(self, interaction: discord.Interaction, mode: bool):
            await update_reset_setting(interaction, mode)

        @app_commands.command(name="set", description="Set count to specific number")
        async def set(self, interaction: discord.Interaction, number: int):
            await counting_set_count(interaction, number)

        @app_commands.command(name="settings", description="Show current channel settings")
        async def counting_link(self, interaction: discord.Interaction):
            await counting_show_settings(interaction)

        @app_commands.command(name="unlink", description="Unlink channel from counting")
        async def counting_unlink(self, interaction: discord.Interaction):
            await counting_unlink_channel(interaction)

    class AdvertiseGroup(app_commands.Group, name="advertise", description="Advertise bot commands"):
        @app_commands.command(name="help", description="Show advertisement bot help")
        async def advertisement_help(self, interaction: discord.Interaction):
            await advertise_help_command(interaction)

        @app_commands.command(name="link", description="Set up current channel for advertisement")
        async def advertisement_link(self, interaction: discord.Interaction, channel: discord.TextChannel, alias: str):
            await link_advertise_channel(interaction, channel, alias)

        @app_commands.command(name="unlink", description="Unlink channel from advertisement")
        async def advertisement_unlink(self, interaction: discord.Interaction, alias: str):
            await unlink_advertise_channel(interaction, alias)

        @app_commands.command(name="settings", description="Set advertisement details")
        async def advertisement_message(self, interaction: discord.Interaction, alias: str):
            await advertisement_settings(interaction, alias)

        @app_commands.command(name="list", description="Show current server advertisement settings")
        async def advertisement_settings(self, interaction: discord.Interaction):
            await show_advertise_settings(interaction)
            return

        @app_commands.command(name="send", description="Send advertisement now")
        async def advertisement_send(self, interaction: discord.Interaction, alias: str):
            await advertise_now(interaction, alias)

        @app_commands.command(name="get", description="Get advertisement message")
        async def advertisement_get(self, interaction: discord.Interaction, alias: str):
            await advertise(interaction, alias)

    async def setup_group_commands(self):
        self.bot.tree.add_command(self.QuanticGroup())
        self.bot.tree.add_command(self.CountingGroup())
        self.bot.tree.add_command(self.AdvertiseGroup())
        await self.bot.tree.sync()

    @commands.command()
    async def h(self, interaction: discord.Interaction):
        await quantic_help_command(interaction)

    @commands.command()
    async def sync(self, ctx: commands.Context):
        await self.bot.tree.sync(guild=discord.Object(id=ctx.guild.id))
        await ctx.send("Commands synced!")

    @commands.command()
    async def lb(self, ctx: commands.Context, count: Optional[int] = 10):
        await show_leaderboard(ctx, count)


@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    setup_database()
    setup_crontabs(client)
    client.add_view(BanButtons())
    await client.add_cog(SlashCommands(client))


@client.event
async def on_message(message):
    await client.process_commands(message)

    if message.author.bot:
        return

    if message.content.startswith('/') or message.content.startswith('!'):
        return

    await counting_chat_evaluation(message)





client.run(TOKEN)