import json
import os
from asyncio import sleep
import random
from datetime import datetime, timedelta
from copy import deepcopy

import discord
from discord.ext import commands, tasks
from dislash import *

from cogs.help import help


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

    def load_timers(self):
        timer_file = open(self.timer_file_path, mode='r')
        self.running_timers = json.load(timer_file)

    def save_timers(self):
        timer_file = open(self.timer_file_path, mode='w')
        json.dump(self.running_timers, timer_file)

    def get_button_row(self, enabled=True):
        button_row = ActionRow(
            Button(
                style=ButtonStyle.grey,
                emoji="🛑",
                custom_id="beenden"
            ),
            Button(
                style=ButtonStyle.grey,
                emoji="🔄",
                custom_id="neustart"
            ),
            Button(
                style=ButtonStyle.grey,
                emoji="⏩",
                custom_id="skip"
            ),
            Button(
                style=ButtonStyle.grey,
                emoji="👍",
                custom_id="anmelden"
            ),
            Button(
                style=ButtonStyle.grey,
                emoji="👎",
                custom_id="abmelden"
            )
        )
        if enabled:
            return button_row
        else:
            button_row.disable_buttons()
            return button_row

    def create_embed(self, name, status, working_time, break_time, remaining, registered):
        color = discord.Colour.green() if status == "Arbeiten" else 0xFFC63A if status == "Pause" else discord.Colour.red()
        descr = "Jetzt: " + status
        zeiten = f"{working_time} Minuten Arbeiten\n{break_time} Minuten Pause"
        remaining_value = f"{remaining} Minuten"
        endzeit = (datetime.now() + timedelta(minutes=remaining)).strftime("%H:%M")
        end_value = f" [bis {endzeit} Uhr]" if status != "Beendet" else ""
        user_list = [self.bot.get_user(int(user_id)) for user_id in registered]
        angemeldet_value = ", ".join([user.mention for user in user_list])

        embed = discord.Embed(title=name,
                              description=descr,
                              color=color)
        embed.add_field(name="Zeiten:", value=zeiten, inline=False)
        embed.add_field(name="verbleibende Zeit:", value=remaining_value + end_value, inline=False)
        embed.add_field(name="angemeldete User:", value=angemeldet_value if registered else "-", inline=False)

        return embed

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
    async def cmd_timer(self, ctx, working_time=25, break_time=5, name=None):
        name = name if name else random.choice(self.default_names)
        remaining = working_time
        status = "Arbeiten"
        registered = [str(ctx.author.id)]

        embed = self.create_embed(name, status, working_time, break_time, remaining, registered)
        msg = await ctx.send(embed=embed, components=[self.get_button_row()])

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
        clicked_button = inter.clicked_button.custom_id

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
        registered = self.running_timers[msg_id]['registered']
        if str(inter.author.id) in self.running_timers[msg_id]['registered']:
            self.running_timers[msg_id]['status'] = "Beendet"
            self.running_timers[msg_id]['remaining'] = 0
            self.running_timers[msg_id]['registered'] = []

            await inter.reply(type=7)
            new_msg_id = await self.edit_message(msg_id)
            await self.make_sound(registered, 'applause.mp3')
            self.running_timers.pop(new_msg_id)
            self.save_timers()

        else:
            # Reply with a hidden message
            await inter.reply("Nur angemeldete Personen können den Timer beenden.", ephemeral=True)

    async def on_neustart_button(self, inter):
        msg_id = str(inter.message.id)
        registered = self.running_timers[msg_id]['registered']
        if str(inter.author.id) in self.running_timers[msg_id]['registered']:
            self.running_timers[msg_id]['status'] = 'Arbeiten'
            self.running_timers[msg_id]['remaining'] = self.running_timers[msg_id]['working_time']
            self.save_timers()

            await inter.reply(type=7)
            new_msg_id = await self.edit_message(msg_id)

            await self.make_sound(registered, 'roll_with_it-outro.mp3')

        else:
            # Reply with a hidden message
            await inter.reply("Nur angemeldete Personen können den Timer neu starten.", ephemeral=True)

    async def on_skip_button(self, inter):
        msg_id = str(inter.message.id)
        registered = self.running_timers[msg_id]['registered']
        if str(inter.author.id) in self.running_timers[msg_id]['registered']:
            new_phase = await self.switch_phase(msg_id)
            if new_phase == "Pause":
                await self.make_sound(registered, 'groove-intro.mp3')
            else:
                await self.make_sound(registered, 'roll_with_it-outro.mp3')
        else:
            # Reply with a hidden message
            await inter.reply("Nur angemeldete Personen können den Timer bedienen.", ephemeral=True)

    async def on_anmelden_button(self, inter):
        msg_id = str(inter.message.id)
        if str(inter.author.id) not in self.running_timers[msg_id]['registered']:
            self.running_timers[msg_id]['registered'].append(str(inter.author.id))
            self.save_timers()
            name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
            embed = self.create_embed(name, status, wt, bt, remaining, registered)
            await inter.reply(embed=embed, components=[self.get_button_row()], type=7)

    async def on_abmelden_button(self, inter):
        msg_id = str(inter.message.id)
        registered = self.running_timers[msg_id]['registered']
        if str(inter.author.id) in registered:
            if len(registered) == 1:
                await self.on_beenden_button(inter)
                return
            else:
                self.running_timers[msg_id]['registered'].remove(str(inter.author.id))
                self.save_timers()
                name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
                embed = self.create_embed(name, status, wt, bt, remaining, registered)
                await inter.reply(embed=embed, components=[self.get_button_row()], type=7)

    async def switch_phase(self, msg_id):
        if self.running_timers[msg_id]['status'] == "Arbeiten":
            self.running_timers[msg_id]['status'] = "Pause"
            self.running_timers[msg_id]['remaining'] = self.running_timers[msg_id]['break_time']
        else:
            self.running_timers[msg_id]['status'] = "Arbeiten"
            self.running_timers[msg_id]['remaining'] = self.running_timers[msg_id]['working_time']
        self.save_timers()

        new_msg_id = await self.edit_message(msg_id)
        return self.running_timers[new_msg_id]['status']

    def get_details(self, msg_id):
        name = self.running_timers[msg_id]['name']
        status = self.running_timers[msg_id]['status']
        wt = self.running_timers[msg_id]['working_time']
        bt = self.running_timers[msg_id]['break_time']
        remaining = self.running_timers[msg_id]['remaining']
        registered = self.running_timers[msg_id]['registered']
        channel = self.running_timers[msg_id]['channel']
        return name, status, wt, bt, remaining, registered, channel

    async def edit_message(self, msg_id, create_new=True):
        channel_id = self.running_timers[msg_id]['channel']
        channel = await self.bot.fetch_channel(int(channel_id))
        msg = await channel.fetch_message(int(msg_id))

        name, status, wt, bt, remaining, registered, _ = self.get_details(msg_id)
        embed = self.create_embed(name, status, wt, bt, remaining, registered)

        if create_new:
            if status == "Beendet":
                new_msg = await channel.send(embed=embed, components=[self.get_button_row(enabled=False)])
            else:
                new_msg = await channel.send(embed=embed, components=[self.get_button_row()])
            self.running_timers[str(new_msg.id)] = self.running_timers[msg_id]
            self.running_timers.pop(msg_id)
            self.save_timers()
            await msg.delete()
            msg = new_msg
        else:
            await msg.edit(embed=embed, components=[self.get_button_row()])
        return str(msg.id)

    async def make_sound(self, registered_users, filename):
        guild = self.bot.get_guild(self.guild_id)
        for user_id in registered_users:
            member = guild.get_member(int(user_id))
            if member.voice:
                channel = member.voice.channel
                if channel:  # If user is in a channel
                    try:
                        voice_client = await channel.connect()
                        voice_client.play(discord.FFmpegPCMAudio(f'cogs/sounds/{filename}'))
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
            if self.running_timers[msg_id]['remaining'] == 0:
                new_phase = await self.switch_phase(msg_id)
                if new_phase == "Pause":
                    await self.make_sound(registered, 'groove-intro.mp3')
                else:
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
