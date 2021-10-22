from disnake.ext import commands
import inspect
import utils
import re
import disnake
import collections

data = {"category": {"__none__": {"title": "Sonstiges", "description": "Die Kategorie für die Kategorielosen."}}, "command": {}}


def help_category(name=None, title=None, description=None, mod_description=None):
    def decorator_help(cmd):
        data["category"][name] = {"title": title, "description": description, "mod_description": mod_description if mod_description else description}
        # if not data["category"][name]:
        #    data["category"][name] = {"description": description}
        # else:
        #    data["category"][name]["description"] = description
        return cmd

    return decorator_help

@help_category("help", "Hilfe", "Wenn du nicht weiter weißt, gib `!help` ein.", "Wenn du nicht weiter weißt, gib `!mod-help` ein.")
def text_command_help(name, syntax=None, example=None, brief=None, description=None, mod=False, parameters={},
                      category=None):
    cmd = re.sub(r"^!", "", name)
    if syntax is None:
        syntax = name
    add_help(cmd, syntax, example, brief, description, mod, parameters, category)


def remove_help_for(name):
    data["command"].pop(name)


def help(syntax=None, example=None, brief=None, description=None, mod=False, parameters={}, category=None, command_group=''):
    def decorator_help(cmd):
        nonlocal syntax, parameters
        cmd_name = f"{command_group} {cmd.name}" if command_group else f"{cmd.name}"
        if syntax is None:
            arguments = inspect.signature(cmd.callback).parameters
            function_arguments = [
                f"<{item[1].name}{'?' if item[1].default != inspect._empty else ''}>" for item in
                list(arguments.items())[2:]]
            syntax = f"!{cmd_name} {' '.join(function_arguments)}"
        add_help(cmd_name, syntax, example, brief,
                 description, mod, parameters, category)
        return cmd

    return decorator_help


def add_help(cmd, syntax, example, brief, description, mod, parameters, category=None):
    if not category:
        category = "__none__"

    data["command"][cmd] = {
        "name": cmd,
        "syntax": syntax.strip(),
        "brief": brief,
        "example": example,
        "description": description,
        "parameters": parameters,
        "mod": mod,
        "category": category
    }


async def handle_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        # syntax = data[ctx.command.name]['syntax']
        # example = data[ctx.command.name]['example']

        cmd_name = f"{ctx.command.parent} {ctx.command.name}" if ctx.command.parent else f"{ctx.command.name}"

        msg = (
            f"Fehler! Du hast ein Argument vergessen. Für weitere Hilfe gib `!help {cmd_name}` ein. \n"
            f"`Syntax: {data['command'][cmd_name]['syntax']}`\n"
        )
        await ctx.channel.send(msg)
    else:
        raise error


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @help(
        category="help",
        brief="Zeigt die verfügbaren Kommandos an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt.",
    )
    @commands.command(name="help")
    async def cmd_help(self, ctx, *command):
        if len(command) > 0:
            command = re.sub(r"^!", "", ' '.join(command))
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx)

    @help(
        category="help",
        brief="Zeigt die verfügbaren Hilfe-Kategorien an.",
        mod=True
    )
    @commands.command(name="help-categories")
    @commands.check(utils.is_mod)
    async def cmd_categories(self, ctx):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'])}
        text = ""
        for key, value in sorted_groups.items():
            text += f"**{key} => {value['title']}**\n"
            text += f"- {value['description']}\n" if value['description'] else ""

        await ctx.channel.send(text)


    @help(
        category="help",
        brief="Zeigt die verfügbaren Kommandos *für Mods* an. Wenn ein Kommando übergeben wird, wird eine ausführliche Hilfe zu diesem Kommando angezeigt. ",
        mod=True
    )
    @commands.command(name="mod-help")
    @commands.check(utils.is_mod)
    async def cmd_mod_help(self, ctx, command=None):
        if not command is None:
            command = re.sub(r"^!", "", command)
            if command == "*" or command == "all":
                await self.help_overview(ctx, mod=True, all=True)
                return
            await self.help_card(ctx, command)
            return
        await self.help_overview(ctx, mod=True)

    async def help_overview(self, ctx, mod=False, all=False):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'] if item[0] != '__none__' else 'zzzzzzzzzzzzzz')}
        sorted_commands = {k: v for k, v in sorted(data["command"].items(), key=lambda item: item[1]['syntax'])}

        title = "Boty hilft dir!"
        help_command = "!help" if not mod else "!mod-help"
        helptext = (f"Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **{help_command} <command>** ein. "
                    f"Also z.B. **{help_command} stats** um mehr über das Statistik-Kommando zu erfahren.")
        helptext += "`!mod-help *` gibt gleichzeitig mod und nicht-mod Kommandos in der Liste aus." if mod else ""
        helptext += "\n\n"
        msgcount = 1

        for key, group in sorted_groups.items():
            text = f"\n__**{group['title']}**__\n"
            text += f"{group['mod_description']}\n" if group.get('mod_description') and mod  else ""
            text += f"{group['description']}\n" if group.get('description') and not mod else ""
            text += "\n"
            for command in sorted_commands.values():

                if (not all and command['mod'] != mod) or command['category'] != key:
                    continue
                # {'*' if command['description'] else ''}\n"
                text += f"**{command['syntax']}**\n"
                text += f"{command['brief']}\n\n" if command['brief'] else "\n"
                if (len(helptext) + len(text) > 2048):
                    embed = disnake.Embed(title=title,
                                          description=helptext,
                                          color=19607)
                    await utils.send_dm(ctx.author, "", embed=embed)
                    helptext = ""
                    msgcount = msgcount + 1
                    title = f"Boty hilft dir! (Fortsetzung {msgcount})"
                helptext += text
                text = ""

        embed = disnake.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)

    async def help_card(self, ctx, name):
        try:
            command = data['command'][name]
            if command['mod'] and not utils.is_mod(ctx):
                return #raise KeyError
        except KeyError:
            await ctx.channel.send(
                "Fehler! Für dieses Kommando habe ich keinen Hilfe-Eintrag. Gib `!help` ein um eine Übersicht zu erhalten. ")
            return
        title = command['name']
        text = f"**{title}**\n"
        text += f"{command['brief']}\n\n" if command['brief'] else ""
        text += f"**Syntax:**\n `{command['syntax']}`\n"
        text += "**Parameter:**\n" if len(command['parameters']) > 0 else ""
        for param, desc in command['parameters'].items():
            text += f"`{param}` - {desc}\n"
        text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
        text += f"\n{command['description']}\n" if command['description'] else ""
        embed = disnake.Embed(title=title,
                              description=text,
                              color=19607)
        text += "==========================\n"
        await utils.send_dm(ctx.author, text)  # , embed=embed)

        for subname in data['command']:
            if subname.startswith(f"{name} "):
                await self.help_card(ctx, subname)

    @commands.command(name="debug-help")
    @commands.check(utils.is_mod)
    async def help_all(self, ctx, mod=False):
        sorted_groups = {k: v for k, v in sorted(data["category"].items(), key=lambda item: item[1]['title'] if item[0] != '__none__' else 'zzzzzzzzzzzzzz')}
        sorted_commands = {k: v for k, v in sorted(data["command"].items(), key=lambda item: item[1]['syntax'])}
        title = "Boty hilft dir!"
        helptext = ("Um ausführliche Hilfe zu einem bestimmten Kommando zu erhalten, gib **!help <command>** ein. "
                    "Also z.B. **!help stats** um mehr über das Statistik-Kommando zu erfahren.\n\n\n")
        msgcount = 1
        for key, group in sorted_groups.items():
            text = f"\n__**{group['title']}**__\n"
            text += f"{group['description']}\n\n" if group['description'] else "\n"
            for command in sorted_commands.values():
                if command['category'] != key:
                    continue
                text += f"**{command['name']}**{' (mods only)' if command['mod'] else ''}\n"
                text += f"{command['brief']}\n\n" if command['brief'] else ""
                text += f"**Syntax:**\n `{command['syntax']}`\n"
                text += "**Parameter:**\n" if len(
                    command['parameters']) > 0 else ""
                for param, desc in command['parameters'].items():
                    text += f"`{param}` - {desc}\n"
                text += f"**Beispiel:**\n `{command['example']}`\n" if command['example'] else ""
                text += f"\n{command['description']}\n" if command['description'] else ""
                text += "=====================================================\n"
                if (len(helptext) + len(text) > 2048):
                    embed = disnake.Embed(title=title,
                                          description=helptext,
                                          color=19607)
                    await utils.send_dm(ctx.author, "", embed=embed)
                    helptext = ""
                    msgcount = msgcount + 1
                    title = f"Boty hilft dir! (Fortsetzung {msgcount})"
                helptext += text
                text = ""

        embed = disnake.Embed(title=title,
                              description=helptext,
                              color=19607)
        await utils.send_dm(ctx.author, "", embed=embed)
