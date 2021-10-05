import datetime
import json
import os
import re

import disnake
from disnake.ext import commands, tasks

import utils
from cogs.help import help

"""
    DISCORD_CALMDOWN_ROLE - Die Rollen-ID der "Calmdown"-Rolle.
    DISCORD_CALMDOWN_FILE - Datendatei. Wenn diese noch nicht existiert wird sie angelegt.
    DISCORD_DATE_TIME_FORMAT - Datumsformat für die interne Speicherung.
"""

class Calmdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_id = int(os.getenv("DISCORD_CALMDOWN_ROLE"))
        self.file = os.getenv("DISCORD_CALMDOWN_FILE")
        self.fmt = os.getenv("DISCORD_DATE_TIME_FORMAT")
        self.silenced_users = {}
        self.load()
        self.timer.start()


    def load(self):
        try:
            file = open(self.file, mode='r')
            self.silenced_users = json.load(file)
        except FileNotFoundError:
            pass

    def save(self):
        file = open(self.file, mode='w')
        json.dump(self.silenced_users, file)

    async def unsilence(self, user_id, guild_id, inform_user=False):
        guild = await self.bot.fetch_guild(int(guild_id))
        role = guild.get_role(self.role_id)

        try:
            user = await guild.fetch_member(int(user_id))
            if inform_user:
                await utils.send_dm(user, f"Die Calmdown-Rolle wurde nun wieder entfernt.")
            await user.remove_roles(role)
        except disnake.errors.NotFound:
            pass

        if self.silenced_users.get(str(user_id)):
            del self.silenced_users[str(user_id)]
            self.save()

    @tasks.loop(minutes=1)
    async def timer(self):
        now = datetime.datetime.now()
        silenced_users = self.silenced_users.copy()
        for user_id, data in silenced_users.items():
            duration = data.get('duration')
            if not duration:
                return
            till = datetime.datetime.strptime(duration, self.fmt)
            if now >= till:
                await self.unsilence(user_id, data['guild_id'], inform_user=True)

    @help(
        brief="Weist einem User die Calmdown-Rolle zu.",
        example="!calmdown @user 1d",
        parameters={
            "user": "Mention des Users, der eine Auszeit benötigt",
            "duration": "Länge der Auszeit (24h für 24 Stunden 7d für 7 Tage oder 10m oder 10 für 10 Minuten. 0 hebt die Sperre auf).",
        },
        description="In der Auszeit darf das Servermitglied noch alle Kanäle lesen. Das Schreiben und Sprechen ist für ihn oder sie allerdings bis zum Ablauf der Zeit gesperrt.",
        mod=True
    )
    @commands.command(name="calmdown", aliases=["auszeit", "mute"])
    @commands.check(utils.is_mod)
    async def cmd_calmdown(self, ctx, user: disnake.Member, duration):
        if re.match(r"^[0-9]+$", duration):
            duration = f"{duration}m"
        if not utils.is_valid_time(duration):
            await ctx.channel.send("Fehler! Wiederholung in ungültigem Format!")
            return
        else:
            guild = ctx.guild
            role = guild.get_role(self.role_id)
            if not role:
                ctx.channel.send("Fehler! Rolle nicht vorhanden!")
                return
            duration = utils.to_minutes(duration)
            if duration == 0:
                await ctx.channel.send(f"{ctx.author.mention} hat {user.mention} aus der **Auszeit** geholt.")
                await self.unsilence(user.id, guild.id, inform_user=False)
                return

            now = datetime.datetime.now()
            till = now + datetime.timedelta(minutes=duration)
            self.silenced_users[str(user.id)] = {"duration": till.strftime(self.fmt), "guild_id": guild.id}
            self.save()
            await ctx.channel.send(f"{ctx.author.mention} hat an {user.mention} die **Calmdown-Rolle** vergeben.")
            await user.add_roles(role)
            if duration < 300:
                await utils.send_dm(user, f"Dir wurde für {duration} Minuten die **Calmdown-Rolle** zugewiesen. Du kannst weiterhin alle Kanäle lesen, aber erst nach Ablauf der Zeit wieder an Gesprächen teilnehmen.")
            else:
                await utils.send_dm(user, f"Bis {till.strftime(self.fmt)} Uhr trägst du die Calmdown-Rolle. Du kannst weiterhin alle Kanäle lesen, aber erst nach Ablauf der Zeit wieder an Gesprächen teilnehmen.")
