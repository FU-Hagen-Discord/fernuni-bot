import base64
import json
import os

from aiohttp import ClientSession
from disnake.ext import commands

import utils
from cogs.help import help, handle_error, help_category


@help_category("github", "Github", "Github Integration in Discord.")
class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.github_file = "data/github.json"
        self.data = self.load()

    def load(self):
        github_file = open(self.github_file, 'r')
        return json.load(github_file)

    def save(self):
        github_file = open(self.github_file, 'w')
        json.dump(self.data, github_file)

    @help(
        category="github",
        syntax="!idee <text>",
        brief="Stellt eine Idee für Boty zur Abstimmung.",
        parameters={
            "text": "Text der Idee.",
        },
        description="Mit diesem Kommando kannst du eine Idee für Boty zur Abstimmung einreichen. Sobald genug "
                    "Reaktionen von anderen Mitgliedern vorhanden sind, wird aus deiner Idee ein Issue in Github "
                    "erstellt, und sobald möglich kümmert sich jemand darum."
    )
    @commands.command(name="idee")
    async def cmd_idee(self, ctx):
        if ctx.channel.id == int(os.getenv("DISCORD_IDEE_CHANNEL")):
            self.data[str(ctx.message.id)] = {"created": False}
            await ctx.message.add_reaction(self.bot.get_emoji(int(os.getenv("DISCORD_IDEE_EMOJI"))))
            self.save()

    @help(
        category="github",
        syntax="!card <text>",
        brief="Erstellt einen Issue in Github.",
        parameters={
            "text": "Text der Idee.",
        },
        description="Mit diesem Kommando kannst du einen Issue in Github anlegen.",
        mod=True
    )
    @commands.command(name="card")
    @commands.check(utils.is_mod)
    async def cmd_card(self, ctx):
        self.data[str(ctx.message.id)] = {"created": False}
        await self.create_issue(self.data[str(ctx.message.id)], ctx.message)
        self.save()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member == self.bot.user:
            return

        if idea := self.data.get(str(payload.message_id)):
            if payload.emoji.id == int(os.getenv("DISCORD_IDEE_EMOJI")):
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                for reaction in message.reactions:
                    if reaction.emoji.id == int(os.getenv("DISCORD_IDEE_EMOJI")):
                        if reaction.count >= int(os.getenv("DISCORD_IDEE_REACT_QTY")) and not idea.get("created"):
                            await self.create_issue(idea, message)

                            self.save()

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)

    async def create_issue(self, idea, message):
        async with ClientSession() as session:
            auth = base64.b64encode(
                f'{os.getenv("DISCORD_GITHUB_USER")}:{os.getenv("DISCORD_GITHUB_TOKEN")}'.encode('utf-8')).decode(
                "utf-8")
            headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

            async with session.post(os.getenv("DISCORD_GITHUB_ISSUE_URL"),
                                    headers=headers,
                                    json={'title': message.content[6:]}) as r:
                if r.status == 201:
                    js = await r.json()

                    idea["created"] = True
                    idea["number"] = js["number"]
                    idea["html_url"] = js["html_url"]

                    await message.reply(
                        f"Danke <@!{message.author.id}> für deinen Vorschlag. Ich habe für dich gerade folgenden Issue in Github erstellt: {idea['html_url']}")
