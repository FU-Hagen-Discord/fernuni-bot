import json
import os
import random
from asyncio import sleep
from copy import deepcopy

import disnake
from disnake import errors, FFmpegPCMAudio
from disnake.ext import commands, tasks

from cogs.help import help
from views import timer_view


class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.guild_id = int(os.getenv('DISCORD_GUILD'))
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot",
                              "Gestiefelter Kater", "Bremer Stadtmusikanten"]
        self.running_timers = {}
        self.timer_file_path = os.getenv("DISCORD_TIMER_FILE")
        self.load_timers()
        self.run_timer.start()
        self.timer_view = timer_view.TimerView()
        bot.add_view(self.timer_view)

    def load_timers(self):
        timer_file = open(self.timer_file_path, mode='r')
        self.running_timers = json.load(timer_file)

    def save_timers(self):
        timer_file = open(self.timer_file_path, mode='w')
        json.dump(self.running_timers, timer_file)

    @help(
        syntax="!timer <working-time?> <break-time?> <name?>",
        brief="Deine persönliche Eieruhr",
        parameters={
            "learning-time": "Länge der Arbeitsphase in Minuten. Default: 25",
            "break-time": "Länge der Pausenphase in Minuten. Default: 5",
            "name": "So soll der Timer heißen. Wird ihm kein Name gegeben, nimmt er sich selbst einen."
        }
    )
    @commands.command(name="timer")
    async def cmd_timer(self, ctx: disnake.ext.commands.Context, working_time: int = 25, break_time: int = 5,
                        name: str = None):
        name = name if name else random.choice(self.default_names)
        remaining = working_time
        status = "Arbeiten"
        registered = [str(ctx.author.id)]

        msg = self.timer_view.send_message(channel=ctx.channel)

        self.running_timers[str(msg.id)] = {'name': name,
                                            'status': status,
                                            'working_time': working_time,
                                            'break_time': break_time,
                                            'remaining': remaining,
                                            'registered': registered,
                                            'channel': ctx.channel.id}
        self.save_timers()
        await self.make_sound(registered, 'roll_with_it-outro.mp3')

    @commands.Cog.listener()
    async def on_button_click(self, inter):
        clicked_button = ""

        if clicked_button == "beenden":
            await self.on_beenden_button(inter)
        elif clicked_button == "neustart":
            await self.on_neustart_button(inter)
        elif clicked_button == "skip":
            await self.on_skip_button(inter)
        elif clicked_button == 'anmelden':
            await self.on_anmelden_button(inter)
        elif clicked_button == "abmelden":
            await self.on_abmelden_button(inter)

    async def on_beenden_button(self, inter):
        msg_id = str(inter.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(inter.author.id) in timer['registered']:
                mentions = self.get_mentions(msg_id)
                timer['status'] = "Beendet"
                timer['remaining'] = 0
                timer['registered'] = []

                await inter.reply(type=7)
                if new_msg_id := await self.edit_message(msg_id, mentions=mentions):
                    await self.make_sound(registered, 'applause.mp3')
                    self.running_timers.pop(new_msg_id)
                    self.save_timers()
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer beenden.", ephemeral=True)
        else:
            await inter.reply("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_neustart_button(self, inter):
        msg_id = str(inter.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(inter.author.id) in timer['registered']:
                timer['status'] = 'Arbeiten'
                timer['remaining'] = timer['working_time']
                self.save_timers()

                await inter.reply(type=7)
                await self.edit_message(msg_id)
                await self.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer neu starten.", ephemeral=True)
        else:
            await inter.reply("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_skip_button(self, inter):
        msg_id = str(inter.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(inter.author.id) in timer['registered']:
                new_phase = await self.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.make_sound(registered, 'groove-intro.mp3')
                else:
                    await self.make_sound(registered, 'roll_with_it-outro.mp3')
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer bedienen.", ephemeral=True)
        else:
            await inter.reply("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_anmelden_button(self, inter):
        msg_id = str(inter.message.id)
        if timer := self.running_timers.get(msg_id):
            if str(inter.author.id) not in timer['registered']:
                timer['registered'].append(str(inter.author.id))
                self.save_timers()
                name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered)
                await inter.reply(embed=embed, components=[self.get_button_row()], type=7)
            else:
                await inter.reply(type=7)
        else:
            await inter.reply("Etwas ist schiefgelaufen...", ephemeral=True)

    async def on_abmelden_button(self, inter):
        msg_id = str(inter.message.id)
        if timer := self.running_timers.get(msg_id):
            registered = timer['registered']
            if str(inter.author.id) in registered:
                if len(registered) == 1:
                    await self.on_beenden_button(inter)
                    return
                else:
                    timer['registered'].remove(str(inter.author.id))
                    self.save_timers()
                    name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                    embed = self.create_embed(name, status, wt, bt, remaining, registered)
                    await inter.reply(embed=embed, components=[self.get_button_row()], type=7)
            else:
                await inter.reply(type=7)
        else:
            await inter.reply("Etwas ist schiefgelaufen...", ephemeral=True)

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
            self.save_timers()

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
                                                     components=[self.get_button_row(enabled=False)])
                    else:
                        new_msg = await channel.send(mentions, embed=embed, components=[self.get_button_row()])
                    self.running_timers[str(new_msg.id)] = self.running_timers[msg_id]
                    self.running_timers.pop(msg_id)
                    self.save_timers()
                    msg = new_msg
                else:
                    await msg.edit(embed=embed, components=[self.get_button_row()])
                return str(msg.id)
            except errors.NotFound:
                self.running_timers.pop(msg_id)
                self.save_timers()
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
                        voice_client.play(FFmpegPCMAudio(f'cogs/sounds/{filename}'))
                        await sleep(3)
                    except errors.ClientException as e:
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

    @cmd_timer.error
    async def timer_error(self, ctx, error):
        await ctx.send("Das habe ich nicht verstanden. Die Timer-Syntax ist:\n"
                       "`!timer <learning-time?> <break-time?> <name?>`\n")
