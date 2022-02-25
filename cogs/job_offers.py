import json
import os
from copy import deepcopy

import aiohttp
from bs4 import BeautifulSoup
import disnake
from disnake import ApplicationCommandInteraction
from disnake.ext import commands, tasks
from cogs.help import help

"""
  Environment Variablen:
  DISCORD_JOBOFFERS_FILE - json file mit allen aktuellen 
  DISCORD_JOBOFFERS_CHANNEL - Channel-ID für Stellenangebote
  DISCORD_JOBOFFERS_URL - URL von der die Stellenangebote geholt werde
  DISCORD_JOBOFFERS_STD_FAK  - Fakultät deren Stellenangebote standtardmäßig gepostet werden
  
  Struktur der json:
  {fak:{id:{title:..., info:..., link:..., deadline:...}}
  mit fak = [mi|rewi|wiwi|ksw|psy]
"""

JOBS_URL = os.getenv("DISCORD_JOBOFFERS_URL")
STD_FAK = os.getenv("DISCORD_JOBOFFERS_STD_FAK")

class Joboffers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.joboffers = {}
        self.joboffers_channel_id = int(os.getenv("DISCORD_JOBOFFERS_CHANNEL"))
        self.joboffers_file = os.getenv("DISCORD_JOBOFFERS_FILE")
        self.load_joboffers()
        self.update_loop.start()

    @tasks.loop(hours=24)
    async def update_loop(self):
        await self.fetch_joboffers()

    @update_loop.before_loop
    async def before_update_loop(self):
        await self.bot.wait_until_ready()

    def save_joboffers(self):
        joboffers_file = open(self.joboffers_file, mode='w')
        json.dump(self.joboffers, joboffers_file)

    def load_joboffers(self):
        try:
            joboffers_file = open(self.joboffers_file, mode='r')
            self.joboffers = json.load(joboffers_file)
        except FileNotFoundError:
            self.joboffers = {}

    @help(
        syntax="/jobs <fak?>",
        parameters={
            "fak": "Fakultät für die die studentische Hilfskraft Jobs ausgegeben werden sollen "
                   "(mi, rewi, wiwi, ksw, psy)"
        },
        brief="Ruft Jobangebote für Studiernde der Fernuni Hagen auf."
    )
    @commands.slash_command(name="jobs", aliases=["offers","stellen","joboffers"],
                            description="Liste Jobangebote der Uni auf",
                            options=[disnake.Option(name="faculty",
                                                    description="Fakultät",
                                                    choices=[disnake.OptionChoice('mi','mi'),
                                                             disnake.OptionChoice('rewi','rewi'),
                                                             disnake.OptionChoice('wiwi','wiwi'),
                                                             disnake.OptionChoice('ksw','ksw'),
                                                             disnake.OptionChoice('psy','psy'),
                                                             disnake.OptionChoice('other','other')])])
    async def cmd_jobs(self, interaction: ApplicationCommandInteraction, faculty: str = STD_FAK):
        await self.fetch_joboffers()

        embed = disnake.Embed(title="Stellenangebote der Uni",
                              description=f"Ich habe folgende Stellenangebote der Fakultät {faculty} gefunden:")
        if offers := self.joboffers.get(faculty):
            for offer_id, offer_data in self.joboffers.get(faculty).items():
                descr = f"{offer_data['info']}\nDeadline: {offer_data['deadline']}\n{offer_data['link']}"
                embed.add_field(name=offer_data['title'], value=descr, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    async def post_new_jobs(self, jobs):
        embed = disnake.Embed(title="Neue Stellenangebote der Uni",
                              description=f"Ich habe folgende neue Stellenangebote der Fakultät {STD_FAK} gefunden:")
        for job in jobs:
            descr = f"{job['info']}\nDeadline: {job['deadline']}\n{job['link']}"
            embed.add_field(name=job['title'], value=descr, inline=False)

        joboffers_channel = await self.bot.fetch_channel(self.joboffers_channel_id)
        await joboffers_channel.send(embed=embed)


    async def fetch_joboffers(self):
        sess = aiohttp.ClientSession()
        req = await sess.get(JOBS_URL)
        text = await req.read()
        await sess.close()

        soup = BeautifulSoup(text, "html.parser")
        list = soup.findAll("li")

        # alte Liste sichern zum Abgleich
        old_joboffers = deepcopy(self.joboffers)

        for job in list:
            detail_string = job.text.strip()
            if "Studentische Hilfskraft" in detail_string:
                id = detail_string[detail_string.index('(')+12:detail_string.index(')')]
                title = detail_string[:detail_string.index(')')+1]
                info = detail_string[detail_string.index(')')+1:detail_string.index('[')]
                deadline = detail_string[detail_string.index('[')+1:detail_string.index(']')]
                link = job.find('a')['href']

                # Umlaute aufräumen
                info = info.replace("Ã¤","ä")
                info = info.replace("Ã¼", "ü")

                faks = ["other", "wiwi", "mi", "ksw", "psy", "rewi"]

                fak_id = int(id[0]) # Kennziffer 1=wiwi, 2=mi, 3=ksw, 4=psy, 5=rewi, alle anderen=other
                if fak_id in range(1,6):
                    fak = faks[fak_id]
                else:
                    fak = faks[0]

                if not self.joboffers.get(fak):
                    self.joboffers[fak] = {}
                self.joboffers[fak][id] = {'title': title, 'info': info, 'deadline': deadline, 'link': link}
        self.save_joboffers()
        await self.check_for_new_jobs(old_joboffers)

    async def check_for_new_jobs(self, old_joboffers):
        new_jobs = []
        if fak := self.joboffers.get(STD_FAK):
            if fak_old := old_joboffers.get(STD_FAK):
                for offer_id, offer_data in self.joboffers.get(STD_FAK).items():
                    if old_offer := fak_old.get(offer_id):
                        if offer_data != old_offer:
                            new_jobs.append(offer_data)
                    else:
                        new_jobs.append(offer_data)
            else:
                for offer_id, offer_data in self.joboffers.get(STD_FAK).items():
                    new_jobs.append(offer_data)
        if new_jobs:
            await self.post_new_jobs(new_jobs)
