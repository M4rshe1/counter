from datetime import datetime
import discord


async def update_embed(interaction, status, color):
    embed = interaction.message.embeds[0]
    embed.set_field_at(4, name='Status', value=status, inline=False)
    embed.add_field(name='processed by', value=f"<@{interaction.user.id}> at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", inline=False)
    embed.color = color
    await interaction.message.edit(embed=embed)
    await interaction.message.edit(view=None)


class BanButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, custom_id="persistent_ban_button")
    async def ban_button(self, interaction, button):
        reason = interaction.message.embeds[0].fields[1].value.replace('> ', '')
        member = interaction.message.embeds[0].fields[0].value.split('<>')[1].replace('@', '')
        member = interaction.guild.get_member(int(member))

        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message('I do not have permission to ban this user!', ephemeral=True)
            return
        await update_embed(interaction, 'Banned', discord.Color.red())
        self.stop()

    @discord.ui.button(label="Remove Timeout", style=discord.ButtonStyle.green, custom_id="persistent_remove_timeout_button")
    async def remove_timeout_button(self, interaction, button):
        member = interaction.message.embeds[0].fields[0].value.split('<')[1].replace('@', '').split('>')[0]
        member = interaction.guild.get_member(int(member))

        try:
            await member.timeout(None)
        except discord.Forbidden:
            await interaction.response.send_message('I do not have permission to remove the timeout!', ephemeral=True)
            return
        await update_embed(interaction, 'Timeout Removed', discord.Color.green())

        self.stop()

    @discord.ui.button(label="Ignore", style=discord.ButtonStyle.grey, custom_id="persistent_ignore_button")
    async def ignore_button(self, interaction, button):
        print("ignoring")
        await update_embed(interaction, 'Ignored', discord.Color.greyple())
        self.stop()