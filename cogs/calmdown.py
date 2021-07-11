import datetime
import os
import re

import discord
from discord.ext import commands, tasks
from tinydb import where

import utils
from cogs.help import help


class Calmdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_id = int(os.getenv("DISCORD_CALMDOWN_ROLE"))
        self.fmt = os.getenv("DISCORD_DATE_TIME_FORMAT")
        self.timer.start()

    @property
    def table(self):
        return self.bot.db.table('silenced_user')

    async def unsilence(self, member: discord.Member, guild):
        role = guild.get_role(self.role_id)
        await member.remove_roles(role)
        self.table.remove(where("member_id") == member.id)

    @tasks.loop(minutes=1)
    async def timer(self):
        now = datetime.datetime.now()
        for silenced_member in self.table.all():
            guild = await self.bot.fetch_guild(silenced_member['guild_id'])
            member = await guild.fetch_member(silenced_member['member_id'])
            if duration := silenced_member.get('duration'):
                till = datetime.datetime.strptime(duration, self.fmt)
                if member and now >= till:
                    await utils.send_dm(member, f"Du darfst die **stille Treppe** nun wieder verlassen.")
                    await self.unsilence(member, guild)

    @help(
        brief="Setzt einen User auf die stille Treppe.",
        example="!calmdown @user 1d",
        parameters={
            "user": "Mention des Users der eine Auszeit benötigt",
            "duration": "Länge der Auszeit (24h für 24 Stunden 7d für 7 Tage oder 10m oder 10 für 10 Minuten. "
                        "0 hebt die Sperre auf).",
        },
        description="In der Zeit auf der stillen Treppe darf der User noch alle Kanäle lesen. "
                    "Das Schreiben ist für ihn allerdings bis zum Ablauf der Zeit gesperrt.",
        mod=True
    )
    @commands.command(name="calmdown", aliases=["auszeit", "mute"])
    @commands.check(utils.is_mod)
    async def cmd_calmdown(self, ctx, member: discord.Member, duration):
        if re.match(r"^[0-9]+$", duration):
            duration = f"{duration}m"
        if not utils.is_valid_time(duration):
            await ctx.channel.send("Fehler! Länge der Auszeit in ungültigem Format!")
            return
        else:
            guild = ctx.guild
            role = guild.get_role(self.role_id)
            if not role:
                await ctx.channel.send("Fehler! Rolle nicht vorhanden!")
                return
            duration = utils.to_minutes(duration)
            if duration == 0:
                await ctx.channel.send(f"{ctx.author.mention} hat {member.mention} von der **stillen Treppe** geholt.")
                await self.unsilence(member, guild)
                return

            now = datetime.datetime.now()
            till = now + datetime.timedelta(minutes=duration)
            self.table.upsert({"member_id": member.id, "duration": till.strftime(self.fmt), "guild_id": guild.id},
                              where("member_id") == member.id)
            await ctx.channel.send(f"{ctx.author.mention} hat {member.mention} auf die **stille Treppe** geschickt.")
            await member.add_roles(role)
            if duration < 300:
                await utils.send_dm(member, f"Du wurdest für {duration} Minuten auf die **stille Treppe** verbannt. "
                                            f"Du kannst weiterhin alle Kanäle lesen, aber erst nach Ablauf der Zeit "
                                            f"wieder an Gesprächen teilnehmen.")
            else:
                await utils.send_dm(member, f"Du wurdest bis {till.strftime(self.fmt)} Uhr auf die **stille Treppe** "
                                            f"verbannt. Du kannst weiterhin alle Kanäle lesen, aber erst nach Ablauf "
                                            f"der Zeit wieder an Gesprächen teilnehmen.")
