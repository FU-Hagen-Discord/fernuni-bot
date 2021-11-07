import json
import uuid

import disnake

from views.dialog_view import DialogView


class ViewManager:

    def __init__(self, bot):
        self.bot = bot
        self.views = {}
        self.functions = {}
        self.load()

    def on_ready(self):
        for view_id in self.views:
            try:
                view = self.build_view(view_id)
                self.bot.add_view(view)
            except:
                pass

    def save(self):
        with open("data/views.json", "w") as file:
            json.dump(self.views, file)

    def load(self):
        with open("data/views.json", "r") as file:
            self.views = json.load(file)

    def register(self, key, func):
        self.functions[key] = func

    async def confirm(self, channel, title, description, custom_prefix, message="", fields=[], callback_key: str = None):
        return await self.dialog(
            channel=channel,
            title=title,
            description=description,
            message=message,
            fields=fields,
            callback_key=callback_key,
            buttons=[
                {"emoji": "👍", "custom_id": f"{custom_prefix}_confirm_yes", "value": True},
                {"emoji": "👎", "custom_id": f"{custom_prefix}_confirm_no", "value": False}
            ]
        )

    async def dialog(self, channel, title, description, message="", fields=[], buttons=None, callback_key: str = None):
        embed = disnake.Embed(title=title,
                              description=description,
                              color=19607)
        for field in fields:
            embed.add_field(**field)
        return await channel.send(message, embed=embed, view=self.view(buttons, callback_key))

    def view(self, buttons=None, callback_key: str = None):
        if buttons is None:
            buttons = []
        view_id = str(uuid.uuid4())
        self.prepare_buttons(buttons, view_id)
        view_config = {"buttons": buttons, "callback_key": callback_key}
        self.views[view_id] = view_config
        self.save()
        return self.build_view(view_id)

    def build_view(self, view_id):
        view_config = self.views[view_id]
        callback_key = view_config["callback_key"]
        func = self.functions[callback_key]
        return DialogView(self.views[view_id]["buttons"], func)

    def add_button(self, config):
        pass

    def prepare_buttons(self, buttons, view_id=None):
        for config in buttons:
            config["custom_id"] = config.get("custom_id", "") + ("" if not view_id else "_" + str(view_id))




