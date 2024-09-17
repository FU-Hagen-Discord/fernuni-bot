import json
import os
import random
from asyncio import sleep
from copy import deepcopy
from datetime import datetime, timedelta

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from views.timer_view import TimerView


class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot",
                              "Gestiefelter Kater", "Bremer Stadtmusikanten"]
        self.timer_file_path = os.getenv("DISCORD_TIMER_FILE")
        self.running_timers = self.load()
        self.load()
        self.run_timer.start()

    def load(self):
        try:
            with open(self.timer_file_path, mode='r') as timer_file:
                return json.load(timer_file)
        except FileNotFoundError:
            return {}

    def save(self):
        with open(self.timer_file_path, mode='w') as timer_file:
            json.dump(self.running_timers, timer_file)

    def get_view(self, disabled=False):
        view = TimerView(self)

        if disabled:
            view.disable()

        return view


    def create_embed(self, name, status, working_time, break_time, remaining, registered):
        color = discord.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else discord.Colour.red()
        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        remaining_value = f"{remaining} Minuten"
        endzeit = (datetime.now() + timedelta(minutes=remaining)).strftime("%H:%M")
        end_value = f" [bis {endzeit} Uhr]" if status != "Beendet" else ""
        user_list = [self.bot.get_user(int(user_id)) for user_id in registered]
        angemeldet_value = ", ".join([user.mention for user in user_list])

        embed = discord.Embed(title=name,
                              color=color)
        embed.add_field(name="Status:", value=status, inline=False)
        embed.add_field(name="Zeiten:", value=zeiten, inline=False)
        embed.add_field(name="Verbleibende Zeit:", value=remaining_value + end_value, inline=False)
        embed.add_field(name="Angemeldete User:", value=angemeldet_value if registered else "-", inline=False)

        return embed

    @app_commands.command(name="timer", description="Erstelle deine persönliche  Eieruhr")
    @app_commands.guild_only()
    async def cmd_timer(self, interaction: Interaction, working_time: int = 25, break_time: int = 5, name: str = None):
        await interaction.response.defer()
        message = await interaction.original_response()
        name = name if name else random.choice(self.default_names)
        remaining = working_time
        status = "Arbeiten"
        registered = [str(interaction.user.id)]

        embed = self.create_embed(name, status, working_time, break_time, remaining, registered)
        await interaction.edit_original_response(embed=embed, view=self.get_view())

        self.running_timers[str(message.id)] = {'name': name,
                                                'status': status,
                                                'working_time': working_time,
                                                'break_time': break_time,
                                                'remaining': remaining,
                                                'registered': registered,
                                                'channel': interaction.channel_id}
        self.save()
        await self.make_sound(registered, 'roll_with_it-outro.mp3')

    async def switch_phase(self, msg_id):
        if timer := self.running_timers.get(msg_id):
            if timer['status'] == "Arbeiten":
                timer['status'] = "Pause"
                timer['remaining'] = timer['break_time']
            elif timer['status'] == "Pause":
                timer['status'] = "Arbeiten"
                timer['remaining'] = timer['working_time']
            else:
                self.running_timers.pop(msg_id)
                return "Beendet"
            self.save()

            if new_msg_id := await self.edit_message(msg_id):
                return self.running_timers[new_msg_id]['status']
            else:
                return "Beendet"

    def get_details(self, msg_id):
        name = self.running_timers[msg_id]['name']
        status = self.running_timers[msg_id]['status']
        wt = self.running_timers[msg_id]['working_time']
        bt = self.running_timers[msg_id]['break_time']
        remaining = self.running_timers[msg_id]['remaining']
        registered = self.running_timers[msg_id]['registered']
        channel = self.running_timers[msg_id]['channel']
        return name, status, wt, bt, remaining, registered, channel

    async def edit_message(self, msg_id, mentions=None, create_new=True):
        if timer := self.running_timers.get(msg_id):
            channel_id = timer['channel']
            channel = await self.bot.fetch_channel(int(channel_id))
            try:
                msg = await channel.fetch_message(int(msg_id))

                name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered)

                if create_new:
                    await msg.delete()
                    if not mentions:
                        mentions = self.get_mentions(msg_id)
                    if status == "Beendet":
                        new_msg = await channel.send(mentions, embed=embed,
                                                     view=self.get_view(disabled=True))
                    else:
                        new_msg = await channel.send(mentions, embed=embed, view=self.get_view())
                    self.running_timers[str(new_msg.id)] = self.running_timers[msg_id]
                    self.running_timers.pop(msg_id)
                    self.save()
                    msg = new_msg
                else:
                    await msg.edit(embed=embed, view=self.get_view())
                return str(msg.id)
            except discord.errors.NotFound:
                self.running_timers.pop(msg_id)
                self.save()
                return None

    def get_mentions(self, msg_id):
        guild = self.bot.get_guild(self.guild_id)
        registered = self.running_timers.get(msg_id)['registered']
        members = [guild.get_member(int(user_id)) for user_id in registered]
        mentions = ", ".join([member.mention for member in members])
        return mentions

    async def make_sound(self, registered_users, filename):
        guild = self.bot.get_guild(self.guild_id)
        for user_id in registered_users:
            member = guild.get_member(int(user_id))
            if member.voice:
                channel = member.voice.channel
                if channel:  # If user is in a channel
                    try:
                        voice_client = await channel.connect()
                        voice_client.play(discord.FFmpegPCMAudio(f'sounds/{filename}'))
                        await sleep(3)
                    except discord.errors.ClientException as e:
                        print(e)
                    for vc in self.bot.voice_clients:
                        await vc.disconnect()
                break

    @tasks.loop(minutes=1)
    async def run_timer(self):
        timers_copy = deepcopy(self.running_timers)
        for msg_id in timers_copy:
            registered = self.running_timers[msg_id]['registered']
            self.running_timers[msg_id]['remaining'] -= 1
            if self.running_timers[msg_id]['remaining'] <= 0:
                new_phase = await self.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.make_sound(registered, 'groove-intro.mp3')
                elif new_phase == "Arbeiten":
                    await self.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                await self.edit_message(msg_id, create_new=False)

    @run_timer.before_loop
    async def before_timer(self):
        await sleep(60)


async def setup(bot: commands.Bot) -> None:
    timer = Timer(bot)
    await bot.add_cog(timer)
    bot.add_view(TimerView(timer))
