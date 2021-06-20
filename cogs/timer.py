from asyncio import sleep
import random

import discord
from discord.ext import tasks, commands
from dislash import *

from cogs.help import help, help_category

class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.countdown = 60     # Sekunden bis zum Refresh der Zeitanzeige
        self.default_names = ["Rapunzel", "Aschenputtel", "Schneewittchen", "Frau Holle", "Schneeweißchen und Rosenrot"]
        SlashClient(bot)        # Stellt den Zugriff auf die Buttons bereit

    @commands.command(name="timer")
    async def cmd_timer(self, ctx, lt=25, bt=5, name=None):
        learning_time = lt
        break_time = bt
        name = name if name else random.choice(self.default_names)
        zeiten = f"{learning_time} Minuten lernen\n{break_time} Minuten Pause"
        status = ["lernen", lt]
        angemeldet = [ctx.author]

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

        async def make_sound(filename):
            async def disconnect():
                for vc in self.bot.voice_clients:
                    await vc.disconnect()

            for user in angemeldet:
                if user.voice:
                    channel = user.voice.channel
                    if channel:  # If user is in a channel
                        voice_client = await channel.connect()
                        try:
                            voice_client.play(discord.FFmpegPCMAudio(f'cogs/sounds/{filename}'))
                            await sleep(2)
                        except discord.errors.ClientException as e:
                            await ctx.send(e)
                        await disconnect()
                    break

        async def ping_users():
            mentions = ", ".join([user.mention for user in angemeldet])
            message = f'{name}: {status[0]}\n{mentions}'
            await ctx.send(message, reference=msg.to_reference(),)

        def create_embed():
            color = discord.Colour.green() if status[0]=="lernen" else 0xFFC63A if status[0]=="Pause" else discord.Colour.red()
            descr = "Jetzt: " + status[0]
            remaining = f"{status[1]} Minuten"
            angemeldet_value = ", ".join([user.mention for user in angemeldet])
            embed = discord.Embed(title=name,
                                  description=descr,
                                  color=color)
            embed.add_field(name="Zeiten:", value=zeiten, inline=False)
            embed.add_field(name="verbleibende Zeit:", value=remaining, inline=False)
            embed.add_field(name="angemeldete User:", value=angemeldet_value if angemeldet else "-", inline=False)
            return embed

        embed = create_embed()
        msg = await ctx.send(embed=embed, components=[button_row])
        await make_sound('boxingbell.mp3')

        on_click = msg.create_click_listener()      # ClickListener für die Buttons

        @on_click.matching_id("beenden")
        async def on_beenden_button(inter):
            nonlocal angemeldet
            if inter.author in angemeldet:
                nonlocal status
                status = ["Beendet", 0]
                button_row.disable_buttons()
                await ping_users()
                angemeldet = []
                embed = create_embed()
                await inter.reply(embed=embed, components=[button_row], type=7)
                await make_sound('applause.mp3')
                on_click.kill()
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer beenden.", ephemeral=True)

        @on_click.matching_id("neustart")
        async def on_neustart_button(inter):
            if inter.author in angemeldet:
                nonlocal status
                status = ["lernen", lt]
                embed = create_embed()
                await inter.reply(embed=embed, components=[button_row], type=7)
                await make_sound('boxingbell.mp3')
                await ping_users()
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer neu starten.", ephemeral=True)

        @on_click.matching_id("skip")
        async def on_skip_button(inter):
            nonlocal status
            if inter.author in angemeldet:
                await switch_phase()
                embed = create_embed()
                await inter.reply(embed=embed, components=[button_row], type=7)
            else:
                # Reply with a hidden message
                await inter.reply("Nur angemeldete Personen können den Timer bedienen.", ephemeral=True)

        @on_click.matching_id("anmelden")
        async def on_anmelden_button(inter):
            if inter.author not in angemeldet:
                angemeldet.append(inter.author)
            embed = create_embed()
            await inter.reply(embed=embed, components=[button_row], type=7)

        @on_click.matching_id("abmelden")
        async def on_abmelden_button(inter):
            if inter.author in angemeldet:
                if len(angemeldet) == 1:
                    await on_beenden_button(inter)
                    return
                else:
                    angemeldet.remove(inter.author)
            embed = create_embed()
            await inter.reply(embed=embed, components=[button_row], type=7)

        async def decrease_remaining_time():
            switch = False
            if status[1] > 0:
                status[1] -= 1
            else:
                await switch_phase()
                switch = True
            return switch

        async def switch_phase():
            nonlocal status
            if status[0] == "lernen":
                status = ["Pause", bt]
                await make_sound('pling.mp3')
            else:
                status = ["lernen", lt]
                await make_sound('bikehorn.mp3')
            await ping_users()

        while status[0] != "Beendet":
            await sleep(self.countdown)
            if status[0] == "Beendet":
                break
            switch = await decrease_remaining_time()
            embed = create_embed()

            if not switch:
                await msg.edit(embed=embed, components=[button_row])
            else:
                #TODO: Ping angemeldete User
                await msg.edit(embed=embed, components=[button_row])
