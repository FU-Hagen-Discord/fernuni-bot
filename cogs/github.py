import base64
import os

from aiohttp import ClientSession
from discord.ext import commands
from tinydb import where

import utils
from cogs.help import help, handle_error, help_category


@help_category("github", "Github", "Github Integration in Discord.")
class Github(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def table(self):
        return self.bot.db.table('github')

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
            self.table.insert({"message_id": ctx.message.id, "created": False})
            await ctx.message.add_reaction(self.bot.get_emoji(int(os.getenv("DISCORD_IDEE_EMOJI"))))

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
        self.table.insert({"message_id": ctx.message.id, "created": False})
        await self.create_issue(ctx.message)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member == self.bot.user:
            return

        if idea := self.table.get(where("message_id") == payload.message_id):
            if payload.emoji.id == int(os.getenv("DISCORD_IDEE_EMOJI")):
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                for reaction in message.reactions:
                    if reaction.emoji.id == int(os.getenv("DISCORD_IDEE_EMOJI")):
                        if reaction.count >= int(os.getenv("DISCORD_IDEE_REACT_QTY")) and not idea.get("created"):
                            await self.create_issue(message)

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)

    async def create_issue(self, message):
        async with ClientSession() as session:
            auth = base64.b64encode(
                f'{os.getenv("DISCORD_GITHUB_USER")}:{os.getenv("DISCORD_GITHUB_TOKEN")}'.encode('utf-8')).decode(
                "utf-8")
            headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

            async with session.post(os.getenv("DISCORD_GITHUB_ISSUE_URL"),
                                    headers=headers,
                                    json={'title': message.content[6:]}) as r:
                if r.status == 201:
                    json = await r.json()

                    self.table.update({"created": True, "number": json["number"], "html_url": json["html_url"]}, where("message_id") == message.id)

                    await message.reply(
                        f"Danke <@!{message.author.id}> für deinen Vorschlag. Ich habe für dich gerade folgenden Issue in Github erstellt: {json['html_url']}")
