from typing import List

import discord


class ModMailView(discord.ui.View):
    def __init__(self, guilds: List[discord.Guild], orig_message, send_modmail):
        super().__init__()
        self.add_item(ServerDropdown(guilds, orig_message, send_modmail))


class ServerDropdown(discord.ui.Select):
    def __init__(self, guilds: List[discord.Guild], orig_message, send_modmail):
        self.guilds = {str(guild.id): guild for guild in guilds}
        self.orig_message = orig_message
        self.send_modmail = send_modmail
        options = [discord.SelectOption(label=guild.name, value=guild_id) for guild_id, guild in self.guilds.items()]

        super().__init__(placeholder='Bitte wähle einen Server aus: ', min_values=0, max_values=1,
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.send_modmail(self.guilds[self.values[0]], self.orig_message)
        await interaction.delete_original_response()
