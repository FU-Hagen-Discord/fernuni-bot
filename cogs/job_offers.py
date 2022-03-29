import json
import os
from copy import deepcopy

import aiohttp
from bs4 import BeautifulSoup
import disnake
from disnake import ApplicationCommandInteraction, MessageInteraction
from disnake.ext import commands, tasks
from disnake.ui import View, Button

from cogs.help import help
from views import joboffers_view

"""
  Environment Variablen:
  DISCORD_JOBOFFERS_FILE - json file mit allen aktuellen 
  DISCORD_JOBOFFERS_CHANNEL - Channel-ID für Stellenangebote
  DISCORD_JOBOFFERS_URL - URL von der die Stellenangebote geholt werde
  DISCORD_JOBOFFERS_STD_FAK  - Fakultät deren Stellenangebote standardmäßig gepostet werden
  
  Struktur der json:
  {fak:{id:{title:..., info:..., link:..., deadline:...}}
  mit fak = [mi|rewi|wiwi|ksw|psy|other]
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
        with open(self.joboffers_file, mode='w') as joboffers_file:
            json.dump(self.joboffers, joboffers_file)

    def load_joboffers(self):
        try:
            with open(self.joboffers_file, mode='r') as joboffers_file:
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
                            description="Liste Jobangebote der Uni auf")
    async def cmd_jobs(self, interaction: ApplicationCommandInteraction,
                       chosen_faculty: str = commands.Param(default=STD_FAK,
                                                            name='faculty',
                                                            choices=['mi','rewi','wiwi','ksw','psy','other','all'])):
        await self.fetch_joboffers()

        fak_text = "aller Fakultäten" if chosen_faculty == 'all' else f"der Fakultät {chosen_faculty}"
        description = f"Ich habe folgende Stellenangebote {fak_text} gefunden:"

        pages = []
        page = []
        for fak, fak_offers in self.joboffers.items():
            if chosen_faculty != 'all' and fak != chosen_faculty:
                continue

            for offer_id, offer_data in fak_offers.items():
                descr = f"{offer_data['info']}\nDeadline: {offer_data['deadline']}\n{offer_data['link']}"
                field = {'name': offer_data['title'], 'value': descr, 'inline': False}
                if len(page) < 5:
                    page.append(field)
                else:
                    pages.append(deepcopy(page))
                    page = []
        if len(page) > 0:
            pages.append(deepcopy(page))

        page_nr = 1
        embed = self.get_embed(description, pages[page_nr-1], page_nr, len(pages))
        view = joboffers_view.JobOffersView(self.on_page_skip, pages, page_nr, description)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def get_embed(self, description, page_content, page_nr, all_pages_nr):
        embed = disnake.Embed(title="Stellenangebote der Uni",
                              description=f"Ich habe folgende Stellenangebote {description} gefunden:")
        for field in page_content:
            embed.add_field(**field)
        embed.set_footer(text=f"Seite {page_nr}/{all_pages_nr}")
        return embed

    async def on_page_skip(self, button: Button, interaction: MessageInteraction, pages, page_nr, embed_description):
        if button.custom_id == "jobs:next":
            page_nr += 1
        if button.custom_id == "jobs:prev":
            page_nr -= 1
        embed = self.get_embed(embed_description, pages[page_nr-1], page_nr, len(pages))
        view = joboffers_view.JobOffersView(self.on_page_skip, pages, page_nr, embed_description)
        await interaction.response.edit_message(embed=embed, view=view)

    async def post_new_jobs(self, jobs):
        fak_text = "aller Fakultäten" if STD_FAK == 'all' else f"der Fakultät {STD_FAK}"
        joboffers_channel = await self.bot.fetch_channel(self.joboffers_channel_id)

        embed = disnake.Embed(title="Neue Stellenangebote der Uni",
                              description=f"Ich habe folgende neue Stellenangebote {fak_text} gefunden:")
        i = 0
        for job in jobs:
            i += 1
            descr = f"{job['info']}\nDeadline: {job['deadline']}\n{job['link']}"
            embed.add_field(name=job['title'], value=descr, inline=False)
            if i % 5 == 0:
                await joboffers_channel.send(embed=embed)
                embed = disnake.Embed(title="Neue Stellenangebote der Uni ... Fortsetzung")
        if i % 5 != 0:
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
        # Liste leeren um outdated joboffers auszusortieren
        self.joboffers = {}

        for job in list:
            detail_string = job.text.strip()
            if "Studentische Hilfskraft" in detail_string:
                id = detail_string[detail_string.index('(')+12:detail_string.index(')')]
                title = detail_string[:detail_string.index(')')+1]
                info = detail_string[detail_string.index(')')+1:detail_string.index('[')]
                deadline = detail_string[detail_string.index('[')+1:detail_string.index(']')]
                link = job.find('a')['href']

                # Sonderzeichen aufräumen
                to_replace = ["Ã¤", "Ã¼", "Â²", "â€ž", "â€œ"]
                replace_with = ["ä", "ü", "²", "\"", "\""]
                for i in range(len(to_replace)):
                    info = info.replace(to_replace[i], replace_with[i])

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

        for fak, fak_offers in self.joboffers.items():
            if STD_FAK != 'all' and fak != STD_FAK:
                continue

            if fak_old := old_joboffers.get(fak):
                for offer_id, offer_data in fak_offers.items():
                    if old_offer := fak_old.get(offer_id):
                        if offer_data != old_offer:
                            new_jobs.append(offer_data)
                    else:
                        new_jobs.append(offer_data)
            else:
                for offer_id, offer_data in self.joboffers.get(fak).items():
                    new_jobs.append(offer_data)

        if new_jobs:
            await self.post_new_jobs(new_jobs)
