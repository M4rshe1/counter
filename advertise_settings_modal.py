import sqlite3

import discord
from discord import ui

from crontabs import delete_cron_job, cron_job
from utils import send_error_message


class AdvertisementSettingsModal(ui.Modal, title="Set Advertisement Details"):
    def __init__(self, alias, message_text=None, image_url_text=None, interval_text=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias = alias
        self.title = f"Set Advertisement Details for {alias}"

        image_url_text = image_url_text if image_url_text else ""
        message_text = message_text if message_text else ""
        interval_text = interval_text if interval_text else ""

        self.add_item(ui.TextInput(label="Message", style=discord.TextStyle.long, default=message_text, required=False))
        self.add_item(ui.TextInput(label="Image URL", style=discord.TextStyle.short, default=image_url_text, required=False, placeholder="https://example.com/image.jpg"))
        self.add_item(ui.TextInput(label="Interval (Cron format -> crontab.guru)", style=discord.TextStyle.short, default=interval_text, required=False, placeholder="* * * * *"))

    async def on_submit(self, interaction: discord.Interaction):
        try :
            message = self.children[0].value if self.children[0].value else None
            image_url = self.children[1].value if self.children[1].value else None
            interval = self.children[2].value if self.children[2].value else None

            conn = sqlite3.connect('quantic.db')
            c = conn.cursor()
            c.execute('UPDATE advetisement SET message = ?, image_url = ?, interval = ? WHERE alias = ? AND server_id = ?',
                      (message, image_url, interval, self.alias, interaction.guild.id))
            conn.commit()
            conn.close()
            delete_cron_job(f"{self.alias}_{interaction.guild.id}")
            if interval:
                cron_job(f"{self.alias}_{interaction.guild.id}", interaction.channel.id, interval, interaction)
            await interaction.response.send_message("Advertisement details updated successfully!")
            await interaction.response.defer()
        except Exception as e:
            print(e)
            send_error_message(interaction, "An error occurred while updating the advertisement details!")