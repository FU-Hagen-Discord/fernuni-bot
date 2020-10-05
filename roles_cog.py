import json
import os

import discord
from discord.ext import commands

import utils


class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roles_file = os.getenv("DISCORD_ROLES_FILE")
        self.assignable_roles = {}
        self.load_roles()

    def load_roles(self):
        """ Loads all assignable roles from ROLES_FILE """

        roles_file = open(self.roles_file, mode='r')
        self.assignable_roles = json.load(roles_file)

    def get_guild(self):
        """ Returns an guild object, that matches the id specified in GUILD.
        This guild is the FU Hagen Informatik/Mathematik guild."""

        for guild in self.bot.guilds:
            if guild.id == int(os.getenv('DISCORD_GUILD')):
                return guild

        return None

    def get_key(self, role):
        """ Get the key for a given role. This role is used for adding or removing a role from a user. """

        for key, role_name in self.assignable_roles.items():
            if role_name == role.name:
                return key

    def get_member(self, user):
        """ Get Member from passed user """

        if type(user) is discord.Member:
            return user
        elif type(user) is discord.User:
            guild = self.get_guild()
            if guild is not None:
                return guild.get_member(user.id)
        return None

    def get_roles(self, user=None):
        """ Get all roles assigned to a member, or all roles available on the discord server
        (in both cases only roles are returned, that are defined in roles.json). """
        roles_list = []
        roles_dict = {}

        if user is not None:
            member = self.get_member(user)
            if member is not None:
                roles_list = member.roles
        else:
            guild = self.get_guild()
            if guild is not None:
                roles_list = guild.roles

        for role in roles_list:
            role_key = self.get_key(role)
            if role_key is not None:
                roles_dict[role_key] = role
        return roles_dict

    @staticmethod
    def get_role_embed(title, roles):
        """ Returns an embed that represents all the roles that are passed to this function """

        embed = discord.Embed(title=title,
                              description="Bei jeder Rolle siehst du oben in Fett den Key der Rolle und "
                                          "darunter den Namen der Rolle",
                              color=19607)
        embed.add_field(name="\u200B", value="\u200B", inline=False)

        for key, role in roles.items():
            embed.add_field(name=key, value=role.name, inline=False)

        return embed

    @commands.command(name="all-roles")
    async def cmd_all_roles(self, message):
        """ Send all available roles that can be assigned to a member by this bot as DM """

        roles = self.get_roles()
        embed = self.get_role_embed("Alle verfügbaren Rollen", roles)
        await utils.send_dm(message.author, "", embed=embed)

    @commands.command(name="my-roles")
    async def cmd_my_roles(self, message):
        """ Send the roles assigned to a member as DM. """

        roles = self.get_roles(message.author)
        embed = self.get_role_embed("Dir zugewiesene Rollen", roles)
        await utils.send_dm(message.author, "", embed=embed)

    @commands.command(name="add-roles")
    async def cmd_add_roles(self, ctx, *args):
        """ Add yourself one or more roles """

        for arg in args:
            await self.modify_roles(ctx.author, True, arg)

    @commands.command(name="remove-roles")
    async def cmd_remove_roles(self, ctx, *args):
        """ Remove roles assigned to you """

        for arg in args:
            await self.modify_roles(ctx.author, False, arg)

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

    async def modify_roles(self, author, add, key):
        """ Add or remove roles assigned to a member. Multiple roles can be added with one command, or removed. """

        guild = self.get_guild()

        if guild is not None:
            member = self.get_member(author)

            roles = self.get_roles()
            if key in roles:
                role = roles[key]
                if add:
                    try:
                        await member.add_roles(role)
                        await utils.send_dm(author, f'Dir wurde die Rolle {role.name} hinzugefügt')
                    except Exception:
                        await utils.send_dm(author, f'Fehler bei der Zuweisung der Rolle {role.name}')
                else:
                    try:
                        await member.remove_roles(role)
                        await utils.send_dm(author, f'Dir wurde die Rolle {role.name} entfernt')
                    except Exception:
                        await utils.send_dm(author, f'Fehler bei der Entfernung der Rolle {role.name}')

    @commands.command(name="stats")
    async def cmd_stats(self, ctx):
        """ Sends stats in Chat. """

        guild = self.get_guild()
        members = await guild.fetch_members().flatten()
        roles = self.get_roles()
        answer = f''
        embed = discord.Embed(title="Statistiken",
                              description=f'Wir haben aktuell {len(members)} Mitglieder auf diesem Server, verteilt auf folgende Rollen:')
        for key, role in roles.items():
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
