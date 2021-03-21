import json
import random
from discord.ext import commands


class EasterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = None
        self.load_data()

    def load_data(self):
        data_file = open("easter.json", mode="r")
        self.data = json.load(data_file)

    def save_data(self):
        data_file = open("easter.json", mode="w")
        json.dump(self.data, data_file)

    @commands.Cog.listener(name="on_message")
    async def hide(self, message):
        if message.channel.id in self.data["channels"]:
            if random.choice(self.data["probability"]):
                await message.add_reaction(random.choice(self.data["reactions"]))

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def seek(self, payload):
        if payload.emoji.name in self.data["reactions"]:
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            for reaction in message.reactions:
                if reaction.emoji == payload.emoji.name:
                    async for user in reaction.users():
                        if user == self.bot.user and reaction.count > 1:
                            self.add_leaderboard(payload.user_id)
                            await message.clear_reaction(reaction)
                            break

    def add_leaderboard(self, user_id):
        if score:= self.data["leaderboard"].get(str(user_id)):
            self.data["leaderboard"][str(user_id)] = score + 1
        else:
            self.data["leaderboard"][str(user_id)] = 1

        self.save_data()

    @commands.command(name="leaderboard")
    async def cmd_leaderboard(self, ctx):
        leaderboard = self.data["leaderboard"]
        place = 8
        max = 10
        ready = False
        message = "```fix\nEgg-Hunt Leaderboard\n\n"
        message += " {:^3} | {:^37} | {:^6}\n".format("#", "Name", "Punkte")
        message += "-----|---------------------------------------|--------\n"
        for key, value in sorted(leaderboard.items(), key=lambda item: item[1], reverse=True):
            try:
                member = await ctx.guild.fetch_member(key)
                place += 1

                if place > max:
                    if ready:
                        break
                    elif str(ctx.author.id) != key:
                        continue
                message += "{:>4} | {:<37} | {:>6}\n".format(str(place), f"{member.display_name}#{member.discriminator}", value)
                if str(ctx.author.id) == key:
                    ready = True
            except:
                pass

        message += "```"
        await ctx.send(message)
