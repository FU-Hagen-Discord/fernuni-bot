import discord


class GroupRequestView(discord.ui.View):
    def __init__(self, learning_groups):
        super().__init__(timeout=None)
        self.learning_groups = learning_groups

    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.green, custom_id="learninggroups:group_yes")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.learning_groups.on_group_request(interaction, confirmed=True)

    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.red, custom_id="learninggroups:group_no")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.learning_groups.on_group_request(interaction, confirmed=False)


class JoinRequestView(discord.ui.View):
    def __init__(self, learning_groups):
        super().__init__(timeout=None)
        self.learning_groups = learning_groups

    @discord.ui.button(emoji="👍", style=discord.ButtonStyle.green, custom_id="learninggroups:join_yes")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.learning_groups.on_join_request(interaction, confirmed=True)

    @discord.ui.button(emoji="👎", style=discord.ButtonStyle.red, custom_id="learninggroups:join_no")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.learning_groups.on_join_request(interaction, confirmed=False)


class ConfirmView(discord.ui.View):
    def __init__(self, user_id: int, confirm_label: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.confirmed = False
        self.confirm.label = confirm_label

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()
