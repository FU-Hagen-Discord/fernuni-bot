import disnake

from views.dialog_view import DialogView


class DialogManager:
    def __init__(self, bot):
        self.bot = bot
        self.views = []
        self.used_custom_ids = []

    def add_confirm(self, custom_prefix, callback):
        yes_id = f"{custom_prefix}_confirm_yes"
        no_id = f"{custom_prefix}_confirm_no"

        return self.add(
            callback=callback,
            buttons=[
                {"emoji": "👍", "value": True, "custom_id": yes_id, "style": disnake.ButtonStyle.green},
                {"emoji": "👎", "value": False, "custom_id": no_id, "style": disnake.ButtonStyle.red}
            ])

    def add(self, callback=None, buttons=None):
        for b in buttons:
            if b.get("custom_id", None) is None:
                raise f"Ein Button hat keine custom_id"
        ids = list(b["custom_id"] for b in buttons)
        if any(x in self.used_custom_ids for x in ids):
            raise "Warnung: Doppelte custom_id"
        self.used_custom_ids.extend(ids)
        view = DialogView(
            callback=callback,
            buttons=buttons
        )
        self.views.append(view)
        self.bot.add_view(view)
        return len(self.views)-1

    async def send(self, dialog_id, channel, title, description, message=""):
        embed = disnake.Embed(title=title,
                              description=description,
                              color=19607)
        return await channel.send(message, embed=embed, view=self.views[dialog_id])


