import discord

from models import Poll, PollParticipant


class PollView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Abstimmen', style=discord.ButtonStyle.green, custom_id='poll_view:vote', emoji="✅")
    async def vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if poll := Poll.get_or_none(Poll.message == interaction.message.id):
            await interaction.response.send_message(
                f"{poll.question}\n\n*(Nach der Abstimmung kannst du diese Nachricht verwerfen. Wenn die Abstimmung "
                f"nicht funktioniert, bitte verwirf die Nachricht und Klicke erneut auf den Abstimmen Button der "
                f"Abstimmung.)*", view=PollChoiceView(poll, interaction.user),
                ephemeral=True)

    @discord.ui.button(label='Beenden', style=discord.ButtonStyle.gray, custom_id='poll_view:close', emoji="🛑")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if poll := Poll.get_or_none(Poll.message == interaction.message.id):
            if interaction.user.id == poll.author:
                poll.delete_instance(recursive=True)
                await interaction.edit_original_response(view=None)

    @discord.ui.button(label='Löschen', style=discord.ButtonStyle.gray, custom_id='poll_view:delete', emoji="🗑")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if poll := Poll.get_or_none(Poll.message == interaction.message.id):
            if interaction.user.id == poll.author:
                poll.delete_instance(recursive=True)
                await interaction.message.delete()


class PollChoiceView(discord.ui.View):
    def __init__(self, poll, user):
        super().__init__(timeout=None)
        self.poll = poll
        self.user = user
        self.add_item(PollDropdown(poll, user))


class PollDropdown(discord.ui.Select):
    def __init__(self, poll, user):
        self.poll = poll
        self.user = user
        options = [discord.SelectOption(label=choice.text, emoji=choice.emoji,
                                        default=len(choice.participants.filter(member_id=user.id)) > 0) for choice in
                   poll.choices]

        super().__init__(placeholder='Gib deine Stimme(n) jetzt ab....', min_values=0, max_values=len(options),
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)
        for choice in self.poll.choices:
            participants = choice.participants.filter(member_id=self.user.id)
            if participants and choice.text not in self.values:
                participants[0].delete_instance()
            elif not participants and choice.text in self.values:
                PollParticipant.create(poll_choice_id=choice.id, member_id=self.user.id)

        message = await interaction.channel.fetch_message(self.poll.message)
        await message.edit(embed=self.poll.get_embed(), view=PollView())