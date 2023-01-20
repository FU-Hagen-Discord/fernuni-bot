import base64
import json
import os

from aiohttp import ClientSession
from discord import app_commands
from discord.ext import commands


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

    @app_commands.command(name="idee", description="Sendet eine Idee für Boty zur Abstimmung ein.")
    @app_commands.describe(text="Text der Idee.")
    @app_commands.guild_only()
    async def cmd_idee(self, interaction, text: str):
        await interaction.response.defer(ephemeral=True)
        channel_id = int(os.getenv("DISCORD_IDEE_CHANNEL"))
        channel = await self.bot.fetch_channel(channel_id)
        message = await channel.send(f"[Neue Weltidee] {text}")
        self.data[str(message.id)] = {"created": False, "user_id": interaction.user.id, "content": text, "html_url": ""}
        await message.add_reaction("👍")
        await interaction.followup.send(f"Danke. Deine Idee wurde in <#{channel_id}> zur Abstimmung vorgeschlagen.")
        self.save()

    @app_commands.command(name="card", description="Mit diesem Kommando kannst du einen Issue in Github anlegen.")
    @app_commands.describe(text="Text der Idee.")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def cmd_card(self, interaction, text: str):
        await interaction.response.send_message("Lege neues Github-Issue an", ephemeral=True)
        idea = {"created": False, "user_id": interaction.user.id, "content": text, "html_url": ""}
        await self.create_issue(idea)
        await interaction.followup.send(
            f"Danke <@!{interaction.user.id}> für deinen Vorschlag. Ich habe für dich gerade folgenden Issue in Github erstellt: {idea['html_url']}")
        self.save()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member == self.bot.user:
            return

        if idea := self.data.get(str(payload.message_id)):
            if payload.emoji.name == os.getenv("DISCORD_IDEE_EMOJI"):
                channel = await self.bot.fetch_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                for reaction in message.reactions:
                    if reaction.emoji == os.getenv("DISCORD_IDEE_EMOJI"):
                        if reaction.count >= int(os.getenv("DISCORD_IDEE_REACT_QTY")) and not idea.get("created"):
                            await self.create_issue(idea)
                            await channel.send(
                                f"Danke <@!{idea['user_id']}> für deinen Vorschlag. Ich habe für dich gerade folgenden Issue in Github erstellt: {idea['html_url']}")
                            self.save()

    async def create_issue(self, idea):
        async with ClientSession() as session:
            auth = base64.b64encode(
                f'{os.getenv("DISCORD_GITHUB_USER")}:{os.getenv("DISCORD_GITHUB_TOKEN")}'.encode('utf-8')).decode(
                "utf-8")
            headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

            async with session.post(os.getenv("DISCORD_GITHUB_ISSUE_URL"),
                                    headers=headers,
                                    json={'title': idea["content"]}) as r:
                if r.status == 201:
                    js = await r.json()

                    idea["created"] = True
                    idea["number"] = js["number"]
                    idea["html_url"] = js["html_url"]
                    idea.pop("content", None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Github(bot))

