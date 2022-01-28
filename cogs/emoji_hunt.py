import json
import random
import disnake
from disnake.ext import commands, tasks
from cogs.help import handle_error


class EmojiHunt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = self.load_data()
        self.messages = []
        self.reaction_timer.start()

    def load_data(self):
        data_file = open("data/emoji_hunt.json", mode="r")
        return json.load(data_file)

    def save_data(self):
        data_file = open("data/emoji_hunt.json", mode="w")
        json.dump(self.data, data_file)

    @commands.Cog.listener(name="on_message")
    async def hide(self, message):
        if message.author == self.bot.user:
            return
    
        if message.channel.id in self.data["channels"]:
            if random.random() < self.data["probability"]:
                self.messages.append(message)
    
    @commands.Cog.listener(name="on_raw_reaction_add")
    async def seek(self, payload):
    
        if payload.member == self.bot.user or payload.message_id not in self.data["message_ids"]:
            return
    
        modifier = 1 if payload.emoji.name in self.data["reactions_add"] else -1 if payload.emoji.name in self.data[
            "reactions_remove"] else 0
        if modifier != 0:
            self.data["message_ids"].remove(payload.message_id)
            self.modify_leaderboard(payload.user_id, modifier)
    
            channel = await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.clear_reaction(payload.emoji.name)
            self.save_data()
    
    def modify_leaderboard(self, user_id, modifier):
        if score := self.data["leaderboard"].get(str(user_id)):
            self.data["leaderboard"][str(user_id)] = score + modifier
        else:
            self.data["leaderboard"][str(user_id)] = modifier
    
        self.save_data()

    @commands.command(name="leaderboard")
    async def cmd_leaderboard(self, ctx, all=None):
        leaderboard = self.data["leaderboard"]
        embed = disnake.Embed(title="Emojijagd Leaderboard", description="Wer hat am meisten Emojis gefunden?")
        embed.set_thumbnail(url="https://external-preview.redd.it/vFsRraBXc5hfUGRWtPPF-NG5maHEPRWTIqamB24whF8.jpg?width=960&crop=smart&auto=webp&s=24d42c9b4f5239a4c3cac79e704b7129c9e2e4d3")

        places = scores = "\u200b"
        place = 0
        max = 0 if all == "all" else 10
        ready = False
        for key, value in sorted(leaderboard.items(), key=lambda item: item[1], reverse=True):
            try:
                place += 1

                if 0 < max < place:
                    if ready:
                        break
                    elif str(ctx.author.id) != key:
                        continue
                places += f"{place}: <@!{key}>\n"
                scores += f"{value:,}\n".replace(",", ".")

                if str(ctx.author.id) == key:
                    ready = True
            except:
                pass

        embed.add_field(name=f"Jägerin", value=places)
        embed.add_field(name=f"Emojis", value=scores)
        await ctx.send("", embed=embed)

    @tasks.loop(seconds=1)
    async def reaction_timer(self):
        delete = []
        for message in self.messages:
            if random.random() < 0.6:
                if random.random() < 0.85:
                    await message.add_reaction(random.choice(self.data["reactions_add"]))
                else:
                    await message.add_reaction(random.choice(self.data["reactions_remove"]))
    
                self.data["message_ids"].append(message.id)
                delete.append(message)
                self.save_data()
    
        if len(delete) > 0:
            for message in delete:
                self.messages.remove(message)

    async def cog_command_error(self, ctx, error):
        await handle_error(ctx, error)
