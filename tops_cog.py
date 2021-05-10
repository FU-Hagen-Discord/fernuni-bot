import json
import os
import re

import discord
from discord.ext import commands


class TopsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tops_file = os.getenv('DISCORD_TOPS_FILE')
        self.tops = {}
        self.load_tops()

    def load_tops(self):
        """ Loads all TOPs from TOPS_FILE """

        tops_file = open(self.tops_file, mode='r')
        self.tops = json.load(tops_file)

    @commands.command(name="add-top")
    async def cmd_add_top(self, ctx, top):
        """ Add TOP to a channel """

        channel = ctx.channel

        if str(channel.id) not in self.tops:
            self.tops[str(channel.id)] = []

        channel_tops = self.tops.get(str(channel.id))
        channel_tops.append(top)

        tops_file = open(self.tops_file, mode='w')
        json.dump(self.tops, tops_file)

    @commands.command(name="remove-top")
    async def cmd_remove_top(self, ctx, top):
        """ Remove TOP from a channel """
        channel = ctx.channel

        if not re.match(r'^-?\d+$', top):
            await ctx.send("Fehler! Der übergebene Parameter muss eine Zahl sein.")
        else:
            if str(channel.id) in self.tops:
                channel_tops = self.tops.get(str(channel.id))

                if 0 < int(top) <= len(channel_tops):
                    del channel_tops[int(top) - 1]

                if len(channel_tops) == 0:
                    self.tops.pop(str(channel.id))

                tops_file = open(self.tops_file, mode='w')
                json.dump(self.tops, tops_file)

    @commands.command(name="clear-tops")
    async def cmd_clear_tops(self, ctx):
        """ Clear all TOPs from a channel """

        channel = ctx.channel

        if str(channel.id) in self.tops:
            self.tops.pop(str(channel.id))
            tops_file = open(self.tops_file, mode='w')
            json.dump(self.tops, tops_file)

    @commands.command(name="tops")
    async def cmd_tops(self, ctx):
        """ Get all TOPs from a channel """

        channel = ctx.channel

        embed = discord.Embed(title="Tagesordnungspunkte",
                              color=19607)
        embed.add_field(name="\u200B", value="\u200B", inline=False)

        if str(channel.id) in self.tops:
            channel_tops = self.tops.get(str(channel.id))

            for i in range(0, len(channel_tops)):
                embed.add_field(name=f"TOP {i + 1}", value=channel_tops[i], inline=False)
        else:
            embed.add_field(name="Keine Tagesordnungspunkte vorhanden.", value="\u200B", inline=False)

        await ctx.send(embed=embed)
