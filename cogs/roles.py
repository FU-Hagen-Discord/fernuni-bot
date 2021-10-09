import json
import os

import disnake
from disnake.ext import commands

import utils
from cogs.help import help, handle_error, help_category


@help_category("updater", "Updater", "Diese Kommandos werden zum Updaten von Nachrichten benutzt, die Boty automatisch erzeugt.")
@help_category("info", "Informationen", "Kleine Helferlein, um schnell an Informationen zu kommen.")
class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_file = os.getenv("DISCORD_ROLES_FILE")
        self.channel_id = int(os.getenv("DISCORD_ROLLEN_CHANNEL", "0"))
        self.degree_program_message_id = int(os.getenv("DISCORD_DEGREE_PROGRAM_MSG", "0"))
        self.color_message_id = int(os.getenv("DISCORD_COLOR_MSG", "0"))
        self.special_message_id = int(os.getenv("DISCORD_SPECIAL_MSG", "0"))
        self.assignable_roles = {}
        self.load_roles()

    def load_roles(self):
        """ Loads all assignable roles from ROLES_FILE """

        roles_file = open(self.roles_file, mode='r')
        self.assignable_roles = json.load(roles_file)

    def get_degree_program_emojis(self):
        """ Creates a dict for degree program role emojis """

        tmp_emojis = {}
        emojis = {}
        degree_program_assignable = self.assignable_roles[0]

        # start with getting all emojis that are used in those roles as a dict
        for emoji in self.bot.emojis:
            if emoji.name in degree_program_assignable:
                tmp_emojis[emoji.name] = emoji

        # bring them in desired order
        for key in degree_program_assignable.keys():
            emojis[key] = tmp_emojis.get(key)

        return emojis

    def get_color_emojis(self):
        """ Creates a dict for color role emojis """

        emojis = {}
        color_assignable = self.assignable_roles[1]

        # start with getting all emojis that are used in those roles as a dict
        for emoji in self.bot.emojis:
            if emoji.name in color_assignable:
                emojis[emoji.name] = emoji

        return emojis

    def get_special_emojis(self):
        """ Creates a dict for special role emojis """

        return self.assignable_roles[2]

    def get_key(self, role):
        """ Get the key for a given role. This role is used for adding or removing a role from a user. """

        for key, role_name in self.assignable_roles[0].items():
            if role_name == role.name:
                return key

    @help(
        category="info",
        brief="Gibt die Mitgliederstatistik aus."
    )
    @commands.command(name="stats")
    async def cmd_stats(self, ctx):
        """ Sends stats in Chat. """

        guild = ctx.guild
        members = await guild.fetch_members().flatten()
        answer = f''
        embed = disnake.Embed(title="Statistiken",
                              description=f'Wir haben aktuell {len(members)} Mitglieder auf diesem Server, verteilt auf folgende Rollen:')

        for role in guild.roles:
            if not self.get_key(role):
                continue
            role_members = role.members
            if len(role_members) > 0 and not role.name.startswith("Farbe"):
                embed.add_field(name=role.name, value=f'{len(role_members)} Mitglieder', inline=False)

        no_role = 0
        for member in members:
            # ToDo Search for study roles only!
            if len(member.roles) == 1:
                no_role += 1

        embed.add_field(name="\u200B", value="\u200b", inline=False)
        embed.add_field(name="Mitglieder ohne Rolle", value=str(no_role), inline=False)

        await ctx.channel.send(answer, embed=embed)

    @help(
        category="updater",
        brief="Aktualisiert die Vergabe-Nachricht von Studiengangs-Rollen.",
        mod=True
    )
    @commands.command("update-degree-program")
    @commands.check(utils.is_mod)
    async def cmd_update_degree_program(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.degree_program_message_id)
        degree_program_emojis = self.get_degree_program_emojis()

        embed = disnake.Embed(title="Vergabe von Studiengangs-Rollen",
                              description="Durch klicken auf die entsprechende Reaktion kannst du dir die damit assoziierte Rolle zuweisen, oder entfernen. Dies funktioniert so, dass ein Klick auf die Reaktion die aktuelle Zuordnung dieser Rolle ändert. Das bedeutet, wenn du die Rolle, die mit <:St:763126549327118366> assoziiert ist, schon hast, aber die Reaktion noch nicht ausgewählt hast, dann wird dir bei einem Klick auf die Reaktion diese Rolle wieder weggenommen. ")

        value = f""
        for key, emoji in degree_program_emojis.items():
            if emoji:
                value += f"<:{key}:{emoji.id}> : {self.assignable_roles[0].get(key)}\n"

        embed.add_field(name="Rollen",
                        value=value,
                        inline=False)

        await message.edit(content="", embed=embed)
        await message.clear_reactions()

        for emoji in degree_program_emojis.values():
            if emoji:
                await message.add_reaction(emoji)

    @help(
        category="updater",
        brief="Aktualisiert die Vergabe-Nachricht von Farb-Rollen.",
        mod=True
    )
    @commands.command("update-color")
    @commands.check(utils.is_mod)
    async def cmd_update_color(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.color_message_id)
        color_emojis = self.get_color_emojis()

        embed = disnake.Embed(title="Vergabe von Farb-Rollen",
                              description="Durch klicken auf die entsprechende Reaktion kannst du dir die damit assoziierte Rolle zuweisen, oder entfernen. Dies funktioniert so, dass ein Klick auf die Reaktion die aktuelle Zuordnung dieser Rolle ändert. Das bedeutet, wenn du die Rolle, die mit <:FarbeGruen:771451407916204052> assoziiert ist, schon hast, aber die Reaktion noch nicht ausgewählt hast, dann wird dir bei einem Klick auf die Reaktion diese Rolle wieder weggenommen. ")

        await message.edit(content="", embed=embed)
        await message.clear_reactions()

        for emoji in color_emojis.values():
            if emoji:
                await message.add_reaction(emoji)

    @help(
        category="updater",
        brief="Aktualisiert die Vergabe-Nachricht von Spezial-Rollen.",
        mod=True
    )
    @commands.command("update-special")
    @commands.check(utils.is_mod)
    async def cmd_update_special(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.special_message_id)
        special_emojis = self.get_special_emojis()

        embed = disnake.Embed(title="Vergabe von Spezial-Rollen",
                              description="Durch klicken auf die entsprechende Reaktion kannst du dir die damit assoziierte Rolle zuweisen, oder entfernen. Dies funktioniert so, dass ein Klick auf die Reaktion die aktuelle Zuordnung dieser Rolle ändert. Das bedeutet, wenn du die Rolle, die mit :exclamation: assoziiert ist, schon hast, aber die Reaktion noch nicht ausgewählt hast, dann wird dir bei einem Klick auf die Reaktion diese Rolle wieder weggenommen. ")

        value = f""
        for emoji, role in special_emojis.items():
            value += f"{emoji} : {role}\n"

        embed.add_field(name="Rollen",
                        value=value,
                        inline=False)

        await message.edit(content="", embed=embed)
        await message.clear_reactions()

        for emoji in special_emojis.keys():
            await message.add_reaction(emoji)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id or payload.message_id not in [self.degree_program_message_id,
                                                                             self.color_message_id,
                                                                             self.special_message_id]:
            return

        if payload.emoji.name not in self.assignable_roles[0] and payload.emoji.name not in self.assignable_roles[
            1] and payload.emoji.name not in self.assignable_roles[2]:
            return

        role_name = ""
        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        roles = member.roles

        await message.remove_reaction(payload.emoji, member)

        if payload.emoji.name in self.assignable_roles[0]:
            role_name = self.assignable_roles[0].get(payload.emoji.name)
        elif payload.emoji.name in self.assignable_roles[1]:
            role_name = self.assignable_roles[1].get(payload.emoji.name)
        else:
            role_name = self.assignable_roles[2].get(payload.emoji.name)

        for role in roles:
            if role.name == role_name:
                await member.remove_roles(role)
                await utils.send_dm(member, f"Rolle \"{role.name}\" erfolgreich entfernt")
                break
        else:
            guild_roles = guild.roles

            for role in guild_roles:
                if role.name == role_name:
                    await member.add_roles(role)
                    await utils.send_dm(member, f"Rolle \"{role.name}\" erfolgreich hinzugefügt")

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
