import json
import os

import disnake
import emoji
from disnake.ext import commands

import utils


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_file = os.getenv("DISCORD_ROLES_FILE")
        self.channel_id = int(os.getenv("DISCORD_ROLLEN_CHANNEL", "0"))
        self.assignable_roles = {}
        self.load_roles()
        self.register_views()

    def load_roles(self):
        """ Loads all assignable roles from ROLES_FILE """

        roles_file = open(self.roles_file, mode='r')
        self.assignable_roles = json.load(roles_file)

    def register_views(self):
        """ Register view for each category at view manager """

        for role_category, roles in self.assignable_roles.items():
            prefix = f"assign_{role_category}"
            self.bot.view_manager.register(prefix, self.on_button_clicked)

    def get_stat_roles(self):
        """ Get all roles that should be part of the stats Command """

        stat_roles = []
        for category in self.assignable_roles.values():
            if category["in_stats"]:
                for role in category["roles"].values():
                    stat_roles.append(role["name"])

        return stat_roles

    async def on_button_clicked(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction, value=None):
        """
        Add or Remove Roles, when Button is clicked. Role gets added, if the user clicking the button doesn't have
        the role already assigned, and removed, if the role is already assigned
        """

        guild_roles = {str(role.id): role for role in interaction.guild.roles}
        role = guild_roles.get(value)

        if role in interaction.author.roles:
            await interaction.author.remove_roles(role)
            await interaction.send(f"Rolle \"{role.name}\" erfolgreich entfernt", ephemeral=True)
        else:
            await interaction.author.add_roles(role)
            await interaction.send(f"Rolle \"{role.name}\" erfolgreich hinzugefügt", ephemeral=True)

    @commands.slash_command(name="update-roles", description="Update Self-Assignable Roles")
    @commands.default_member_permissions(moderate_members=True)
    async def cmd_update_roles(self, interaction: disnake.ApplicationCommandInteraction):
        """ Update all role assignment messages in role assignment channel """
        await interaction.response.defer(ephemeral=True)

        channel = await interaction.guild.fetch_channel(self.channel_id)
        await channel.purge()
        for role_category, roles in self.assignable_roles.items():
            prefix = f"assign_{role_category}"
            fields = []
            buttons = []
            value = f""
            guild_roles = {role.name: role for role in interaction.guild.roles}

            for key, role in roles.get("roles").items():
                role_emoji = role.get('emoji') if role.get(
                    'emoji') in emoji.UNICODE_EMOJI_ALIAS_ENGLISH else f"<{role.get('emoji')}>"
                value += f"{role_emoji} : {role.get('name')}\n"
                buttons.append({"emoji": role_emoji, "custom_id": f"{prefix}_{key}",
                                "value": f"{str(guild_roles.get(role.get('name')).id)}"})

            if roles.get("list_roles"):
                fields.append({"name": "Rollen", "value": value, "inline": False})

            await self.bot.view_manager.dialog(
                channel=channel,
                title=f"Vergabe von {roles.get('name')}",
                description="Durch klicken auf den entsprechenden Button kannst du dir die damit "
                            "assoziierte Rolle zuweisen, bzw. entfernen.",
                message="",
                fields=fields,
                callback_key=prefix,
                buttons=buttons
            )

        await interaction.edit_original_message("Rollen erfolgreich aktualisiert.")

    @commands.slash_command(name="stats", description="Rollen Statistik abrufen")
    async def cmd_stats(self, interaction: disnake.ApplicationCommandInteraction, show: bool = False):
        """
        Send role statistics into chat, by default as ephemeral

        Parameters
        ----------
        show: Sichtbar für alle?
        """

        guild = interaction.guild
        members = await guild.fetch_members().flatten()
        guild_roles = {role.name: role for role in interaction.guild.roles}
        stat_roles = self.get_stat_roles()
        embed = disnake.Embed(title="Statistiken",
                              description=f'Wir haben aktuell {len(members)} Mitglieder auf diesem Server, '
                                          f'verteilt auf folgende Rollen:')

        for role_name in stat_roles:
            role = guild_roles[role_name]
            role_members = role.members
            num_members = len(role_members)
            if num_members > 0:
                embed.add_field(name=role.name,
                                value=f'{num_members} {"Mitglieder" if num_members > 1 else "Mitglied"}', inline=False)

        await interaction.send(embed=embed, ephemeral=not show)
