import disnake
from disnake import MessageInteraction, ButtonStyle
from disnake.ui import Button, View

NEXT = "jobs:next"
PREV = "jobs:prev"


class JobOffersView(View):
    def __init__(self, callback, list_of_pages, actual_page_nr, embed_description):
        super().__init__(timeout=None)
        self.callback = callback
        self.list_of_pages = list_of_pages
        self.actual_page_nr = actual_page_nr
        self.embed_description = embed_description
        if actual_page_nr == 1:
            self.disable_prev()
        if actual_page_nr == len(self.list_of_pages):
            self.disable_next()

    @disnake.ui.button(emoji="⬅", custom_id=PREV)
    async def btn_prev(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction, self.list_of_pages, self.actual_page_nr, self.embed_description)

    @disnake.ui.button(emoji="➡", custom_id=NEXT)
    async def btn_next(self, button: Button, interaction: MessageInteraction):
        await self.callback(button, interaction, self.list_of_pages, self.actual_page_nr, self.embed_description)

    def disable_prev(self):
        prev_button = self.children[0]
        prev_button.disabled = True

    def disable_next(self):
        next_button = self.children[1]
        next_button.disabled = True