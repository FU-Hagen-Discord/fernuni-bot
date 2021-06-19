from asyncio import sleep

import discord
from discord.ext import tasks, commands
from dislash import *

from cogs.help import help, help_category

class Timer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.counter = 0        # Anzahl aktiver Timer
        self.countdown = 10     # Sekunden bis zum Refresh der Zeitanzeige
        SlashClient(bot)        # Stellt den Zugriff auf die Buttons bereit

    @commands.command(name="timer")
    async def cmd_timer(self, ctx, lt=25, bt=5, name=None):
        self.counter += 1
        learning_time = lt
        break_time = bt
        name = name if name else f"Timer #{self.counter}"
        zeiten = f"{learning_time} Minuten lernen\n{break_time} Minuten Pause"
        running = True

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
        )

        def create_embed(remaining_time, active, running=True):
            color = discord.Colour.green() if active else 0xFFC63A if running else discord.Colour.red()
            status = "lernen" if active else "Pause" if running else "Beendet"
            descr = "Jetzt: " + status
            remaining = f"{remaining_time} Minuten" if running else "Beendet"
            embed = discord.Embed(title=name,
                                  description=descr,
                                  color=color)
            embed.add_field(name="Zeiten:", value=zeiten, inline=False)
            embed.add_field(name="verbleibende Zeit:", value=remaining, inline=False)
            return embed

        embed = create_embed(learning_time, active=True)
        msg = await ctx.send(embed=embed, components=[button_row])

        on_click = msg.create_click_listener()

        @on_click.not_from_user(ctx.author, cancel_others=True)
        async def on_wrong_user(inter):
            # Reply with a hidden message
            await inter.reply("Nur die Person, die den Timer erstellt hat, kann ihn auch bedienen.", ephemeral=True)

        @on_click.matching_id("beenden")
        async def on_beenden_button(inter):
            nonlocal running
            button_row.disable_buttons()
            await inter.reply(content="Beendet", components=[button_row], type=7)
            on_click.kill()
            self.counter -= 1
            running = False

        @on_click.matching_id("neustart")
        async def on_neustart_button(inter):
            await inter.reply("Neustart", type=7)


        async def decrease_remaining_time():
            while (running):
                for i in range(learning_time+1):
                    await sleep(self.countdown)
                    embed = create_embed(learning_time - i, active=True)
                    await msg.edit(embed=embed, components=[button_row])
                    if not running:
                        break

                for i in range(break_time+1):
                    await sleep(self.countdown)
                    embed = create_embed(break_time - i, active=False)
                    await msg.edit(embed=embed, components=[button_row])
                    if not running:
                        break

            embed = create_embed(break_time - i, active=False, running=False)
            await msg.edit(embed=embed, components=[button_row])

        await decrease_remaining_time()
