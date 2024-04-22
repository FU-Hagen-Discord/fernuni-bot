from discord import Member
from discord.ext import commands


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member) -> None:
        if before.pending != after.pending and not after.pending:
            channel_id = self.bot.get_settings(before.guild.id).greeting_channel_id
            channel = await self.bot.fetch_channel(channel_id)
            await channel.send(f"Herzlich Willkommen <@!{before.id}> im Kreise der Studentinnen :wave:")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))
