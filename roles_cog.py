import json
import os

import discord
from discord.ext import commands

import utils


def get_student_role(guild):
    student_role_id = int(os.getenv("DISCORD_STUDENTIN_ROLE"))

    for role in guild.roles:
        if role.id == student_role_id:
            return role

    return None


class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_file = os.getenv("DISCORD_ROLES_FILE")
        self.channel_id = int(os.getenv("DISCORD_ROLLEN_CHANNEL"))
        self.degree_program_message_id = int(os.getenv("DISCORD_DEGREE_PROGRAM_MSG"))
        self.color_message_id = int(os.getenv("DISCORD_COLOR_MSG"))
        self.special_message_id = int(os.getenv("DISCORD_SPECIAL_MSG"))
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

    @commands.command(name="add-role")
    @commands.is_owner()
    async def cmd_add_role(self, ctx, key, role):
        """ Add a Role to be assignable (Admin-Command only) """

        self.assignable_roles[key] = role
        roles_file = open(self.roles_file, mode='w')
        json.dump(self.assignable_roles, roles_file)

        if key in self.assignable_roles:
            await utils.send_dm(ctx.author, f"Rolle {role} wurde hinzugefügt")
        else:
            await utils.send_dm(ctx.author, f"Fehler beim Hinzufügen der Rolle {role}")

    @commands.command(name="stats")
    async def cmd_stats(self, ctx):
        """ Sends stats in Chat. """

        guild = ctx.guild
        members = await guild.fetch_members().flatten()
        answer = f''
        embed = discord.Embed(title="Statistiken",
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

    @commands.command("update-degree-program")
    @commands.check(utils.is_mod)
    async def cmd_update_degree_program(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.degree_program_message_id)
        degree_program_emojis = self.get_degree_program_emojis()

        embed = discord.Embed(title="Vergabe von Studiengangs-Rollen",
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

    @commands.command("update-color")
    @commands.check(utils.is_mod)
    async def cmd_update_color(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.color_message_id)
        color_emojis = self.get_color_emojis()

        embed = discord.Embed(title="Vergabe von Farb-Rollen",
                              description="Durch klicken auf die entsprechende Reaktion kannst du dir die damit assoziierte Rolle zuweisen, oder entfernen. Dies funktioniert so, dass ein Klick auf die Reaktion die aktuelle Zuordnung dieser Rolle ändert. Das bedeutet, wenn du die Rolle, die mit <:FarbeGruen:771451407916204052> assoziiert ist, schon hast, aber die Reaktion noch nicht ausgewählt hast, dann wird dir bei einem Klick auf die Reaktion diese Rolle wieder weggenommen. ")

        await message.edit(content="", embed=embed)
        await message.clear_reactions()

        for emoji in color_emojis.values():
            if emoji:
                await message.add_reaction(emoji)

    @commands.command("update-special")
    @commands.check(utils.is_mod)
    async def cmd_update_special(self, ctx):
        channel = await self.bot.fetch_channel(self.channel_id)
        message = await channel.fetch_message(self.special_message_id)
        special_emojis = self.get_special_emojis()

        embed = discord.Embed(title="Vergabe von Spezial-Rollen",
                              description="Durch klicken auf die entsprechende Reaktion kannst du dir die damit assoziierte Rolle zuweisen, oder entfernen. Dies funktioniert so, dass ein Klick auf die Reaktion die aktuelle Zuordnung dieser Rolle ändert. Das bedeutet, wenn du die Rolle, die mit <:FarbeGruen:771451407916204052> assoziiert ist, schon hast, aber die Reaktion noch nicht ausgewählt hast, dann wird dir bei einem Klick auf die Reaktion diese Rolle wieder weggenommen. ")

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
        student_role = None
        guild = await self.bot.fetch_guild(payload.guild_id)
        member = await guild.fetch_member(payload.user_id)
        channel = await self.bot.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        roles = member.roles

        await message.remove_reaction(payload.emoji, member)

        if payload.emoji.name in self.assignable_roles[0]:
            role_name = self.assignable_roles[0].get(payload.emoji.name)
            student_role = get_student_role(guild)
        elif payload.emoji.name in self.assignable_roles[1]:
            role_name = self.assignable_roles[1].get(payload.emoji.name)
        else:
            role_name = self.assignable_roles[2].get(payload.emoji.name)

        for role in roles:
            if role.name == role_name:
                if not role == student_role:
                    await member.remove_roles(role)
                    await utils.send_dm(member, f"Rolle \"{role.name}\" erfolgreich entfernt")
                break
        else:
            guild_roles = guild.roles

            for role in guild_roles:
                if role.name == role_name:
                    await member.add_roles(role)
                    await utils.send_dm(member, f"Rolle \"{role.name}\" erfolgreich hinzugefügt")
                    if student_role and not role == student_role:
                        await member.add_roles(student_role)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if len(before.roles) != len(after.roles):
            roles_before = before.roles
            roles_after = after.roles
            for role in roles_before:
                if role in roles_after:
                    roles_after.remove(role)

            if len(roles_after) > 0:
                if roles_after[0].id == int(os.getenv("DISCORD_STUDENTIN_ROLE")):
                    channel = await self.bot.fetch_channel(int(os.getenv("DISCORD_GREETING_CHANNEL")))
                    await channel.send(f"Herzlich Willkommen <@!{before.id}> im Kreise der Studentinnen :wave:")
