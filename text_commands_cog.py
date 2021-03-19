import json
import os
import random

import discord
from discord.ext import commands

import utils


class TextCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.text_commands = {}
        self.cmd_file = os.getenv("DISCORD_TEXT_COMMANDS_FILE")
        self.load_text_commands()

    def load_text_commands(self):
        """ Loads all appointments from APPOINTMENTS_FILE """

        text_commands_file = open(self.cmd_file, mode='r')
        self.text_commands = json.load(text_commands_file)

    def save_text_commands(self):
        text_commands_file = open(self.cmd_file, mode='w')
        json.dump(self.text_commands, text_commands_file)

    @commands.Cog.listener(name="on_message")
    async def process_text_commands(self, message):
        if message.author == self.bot.user:
            return

        cmd = message.content.split(" ")[0]
        texts = self.text_commands.get(cmd)

        if texts:
            await message.channel.send(random.choice(texts))

    @commands.command(name="add-text-command")
    @commands.check(utils.is_mod)
    async def cmd_add_text_command(self, ctx, cmd, text):
        texts = self.text_commands.get(cmd)

        if texts:
            texts.append(text)
        else:
            self.text_commands[cmd] = [text]

        self.save_text_commands()

        await ctx.send(f"[{cmd}] => [{text}] erfolgreich hinzugefügt.")

    @commands.command(name="text-commands")
    @commands.check(utils.is_mod)
    async def cmd_text_commands(self, ctx):
        answer = f"Text Commands:\n"

        ctr = 0
        for command in self.text_commands:
            answer += f"{ctr}: {command}\n"
            ctr += 1

        await ctx.send(answer)

    @commands.command(name="texts")
    @commands.check(utils.is_mod)
    async def cmd_texts(self, ctx, cmd):
        texts = self.text_commands.get(cmd)
        answer = f"Für {cmd} hinterlegte Texte: \n"

        for i in range(0, len(texts)):
            text = texts[i]
            if len(answer) + len(text) > 2000:
                await ctx.send(answer)
                answer = f""

            answer += f"{i}: {text}\n"

        await ctx.send(answer)

    @commands.command(name="edit-text")
    @commands.check(utils.is_mod)
    async def cmd_edit_text(self, ctx, cmd, id, text):
        texts = self.text_commands.get(cmd)

        if texts:
            i = int(id)
            if i < len(texts):
                texts[i] = text
                await ctx.send(f"Text {i} für Command {cmd} wurde erfolgreich geändert")
                self.save_text_commands()
            else:
                await ctx.send(f"Ungültiger Index")
        else:
            await ctx.send("Command {cmd} nicht vorhanden!")

    @commands.command(name="remove-text")
    @commands.check(utils.is_mod)
    async def cmd_remove_text(self, ctx, cmd, id):
        texts = self.text_commands.get(cmd)

        if texts:
            i = int(id)
            if i < len(texts):
                del texts[i]
                await ctx.send(f"Text {i} für Command {cmd} wurde erfolgreich entfernt")

                if len(texts) == 0:
                    self.text_commands.pop(cmd)

                self.save_text_commands()
            else:
                await ctx.send(f"Ungültiger Index")
        else:
            await ctx.send("Command {cmd} nicht vorhanden!")

    @commands.command(name="remove-text-command")
    @commands.check(utils.is_mod)
    async def cmd_remove_text_command(self, ctx, cmd):
        if cmd in self.text_commands:
            self.text_commands.pop(cmd)
            await ctx.send(f"Text Command {cmd} wurde erfolgreich entfernt")
            self.save_text_commands()
        else:
            await ctx.send(f"Text Command {cmd} nicht vorhanden")

    @commands.command(name="add-motivation")
    async def cmd_add_motivation(self, ctx, *text):
        mod_channel = await self.bot.fetch_channel(int(os.getenv("DISCORD_MOD_CHANNEL")))

        embed = discord.Embed(title="Neuer Motivations Text",
                              description=f"<@!{ctx.author.id}> Möchte folgenden Motivationstext hinzufügen:")
        embed.add_field(name="\u200b", value=f'{" ".join(text)}')

        message = await mod_channel.send(embed=embed)
        await message.add_reaction("👍")
        await utils.send_dm(ctx.author,
                            "Dein Motivationstext wurde den Mods zur Genehmigung vorgelegt. Sobald er angenommen wurde, erhältst du eine Benachrichtigung.")

    async def motivation_approved(self, message):
        embed = message.embeds[0]
        text = embed.fields[0].value
        description = embed.description
        ctx = await self.bot.get_context(message)
        member_id = description[3:21]
        guild = message.guild
        member = await guild.fetch_member(member_id)

        await utils.send_dm(member,
                            f"Herzlichen Glückwunsch, dein Vorschlag für einen neuen Motivationstext wurde angenommen.\n\n{text}")
        await self.cmd_add_text_command(ctx, "!motivation", text)
        await message.delete()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.emoji.name in ["👍"]:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds) > 0 and message.embeds[0].title == "Neuer Motivations Text":
                await self.motivation_approved(message)
