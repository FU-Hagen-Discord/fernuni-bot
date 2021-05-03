from discord.ext import commands
import inspect
import itertools
from functools import wraps
import utils
import re
import discord
import collections
data = {}


def text_command_help(name, syntax=None, example=None, brief=None, description=None, mod=False, parameters={}):
    cmd = re.sub(r"^!", "", name)
    if syntax is None:
        syntax = name
    add_help(cmd, syntax, example, brief, description, mod, parameters)


def remove_help_for(name):
    data.pop(name)


def help(syntax=None, example=None, brief=None, description=None, mod=False, parameters={}):
    def decorator_help(cmd):
        nonlocal syntax, parameters
        if syntax is None:
            arguments = inspect.signature(cmd.callback).parameters
            function_arguments = [
                f"<{item[1].name}{'?' if item[1].default != inspect._empty else ''}>" for item in list(arguments.items())[2:]]
            syntax = f"!{cmd.name} {' '.join(function_arguments)}"
        add_help(cmd.name, syntax, example, brief,
                 description, mod, parameters)
        return cmd
    return decorator_help


def add_help(cmd, syntax, example, brief, description, mod, parameters):
    data[cmd] = {
        "name": cmd,
        "syntax": syntax.strip(),
        "brief": brief,
        "example": example,
        "description": description,
        "parameters": parameters,
        "mod": mod
    }


async def handle_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        syntax = data[ctx.command.name]['syntax']
        example = data[ctx.command.name]['example']

        msg = (
            f"Fehler! Du hast ein Argument vergessen. Für weitere Hilfe gib `!help {ctx.command.name}` ein. \n"
            f"`Syntax: {data[ctx.command.name]['syntax']}`\n"
        )
        await ctx.channel.send(msg)
    else:
        raise error


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
        brief="Zeigt die verfügbaren Kommandos an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt.",
    )
    @commands.command(name="help")
    async def cmd_help(self, ctx, command=None):
        if not command is None:
            command = re.sub(r"^!", "", command)
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx)

    @help(
        brief="Zeigt die verfügbaren Kommandos *für Mods* an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt.",
        mod=True
    )
    @commands.command(name="mod-help")
    @commands.check(utils.is_mod)
    async def cmd_mod_help(self, ctx, command=None):
        if not command is None:
            command = re.sub(r"^!", "", command)
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx, True)

    async def help_overview(self, ctx, mod=False):
        sorted_commands = collections.OrderedDict(sorted(data.items()))
        title = "Boty hilft dir!"
        helptext = ("Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **!help <command>** ein. "
                    "Also z.B. **!help stats** um mehr über das Statistik-Kommando zu erfahren.\n\n")
        msgcount = 1
        for command in sorted_commands.values():
            text = ""
            if command['mod'] != mod:
                continue
            # {'*' if command['description'] else ''}\n"
            text += f"**{command['syntax']}**\n"
            text += f"{command['brief']}\n\n" if command['brief'] else "\n"
            if (len(helptext) + len(text) > 2048):
                embed = discord.Embed(title=title,
                                      description=helptext,
                                      color=19607)
                await utils.send_dm(ctx.author, "", embed=embed)
                helptext = ""
                msgcount = msgcount + 1
                title = f"Boty hilft dir! (Fortsetzung {msgcount})"
            helptext += text

        embed = discord.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)

    async def help_card(self, ctx, name):
        try:
            command = data[name]
            if command['mod'] == True and not utils.is_mod(ctx):
              raise KeyError
        except KeyError:
            await ctx.channel.send("Fehler! Für dieses Kommando habe ich keinen Hilfe-Eintrag. Gib `!help` ein um eine Übersicht zu erhalten. ")
            return
        title = command['name']
        text = f"**{title}**\n"
        text += f"{command['brief']}\n\n" if command['brief'] else ""
        text += f"**Syntax:**\n `{command['syntax']}`\n"
        text += "**Paramter:**\n" if len(command['parameters']) > 0 else ""
        for param, desc in command['parameters'].items():
            text += f"`{param}` - {desc}\n"
        text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
        text += f"\n{command['description']}\n" if command['description'] else ""
        embed = discord.Embed(title=title,
                              description=text,
                              color=19607)
        await utils.send_dm(ctx.author, text)  # , embed=embed)

    @commands.command(name="all-help")
    @commands.check(utils.is_mod)
    async def help_all(self, ctx, mod=False):
        sorted_commands = collections.OrderedDict(sorted(data.items()))
        title = "Boty hilft dir!"
        helptext = ("Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **!help <command>** ein. "
                    "Also z.B. **!help stats** um mehr über das Statistik-Kommando zu erfahren.\n\n\n")
        msgcount = 1
        for command in sorted_commands.values():
            text = f"**{command['name']}**{' (mods only)' if command['mod'] else ''}\n"
            text += f"{command['brief']}\n\n" if command['brief'] else ""
            text += f"**Syntax:**\n `{command['syntax']}`\n"
            text += "**Paramter:**\n" if len(command['parameters']) > 0 else ""
            for param, desc in command['parameters'].items():
                text += f"`{param}` - {desc}\n"
            text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
            text += f"\n{command['description']}\n" if command['description'] else ""
            text += "=====================================================\n"
            if (len(helptext) + len(text) > 2048):
                embed = discord.Embed(title=title,
                                      description=helptext,
                                      color=19607)
                await utils.send_dm(ctx.author, "", embed=embed)
                helptext = ""
                msgcount = msgcount + 1
                title = f"Boty hilft dir! (Fortsetzung {msgcount})"
            helptext += text

        embed = discord.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)
