import discord

import utils


async def show_participants(interaction, poll, ephemeral):
    msg = f"Teilnehmer der Umfrage `{poll['question']}`:\n"
    participant_choices = [[] for _ in range(len(poll["choices"]))]
    for participant, choices in poll["participants"].items():
        for choice in choices:
            participant_choices[choice].append(participant)

    choices = poll["choices"]
    for idx, participants in enumerate(participant_choices):
        choice_msg = f"{choices[idx][0]} {choices[idx][1]} ({choices[idx][2]}):"
        choice_msg += "<@" if choices[idx][2] > 0 else ""
        choice_msg += ">, <@".join(participants)
        choice_msg += ">\n" if choices[idx][2] > 0 else ""
        if len(msg) + len(choice_msg) >= utils.MAX_MESSAGE_LEN:
            await interaction.followup.send(msg, ephemeral=ephemeral)
            msg = choice_msg
        else:
            msg += choice_msg

    await interaction.followup.send(msg, ephemeral=ephemeral)


class PollView(discord.ui.View):
    def __init__(self, polls):
        super().__init__(timeout=None)
        self.polls = polls

    @discord.ui.button(label='Abstimmen', style=discord.ButtonStyle.green, custom_id='poll_view:vote', emoji="✅")
    async def vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if poll := self.polls.polls.get(str(interaction.message.id)):
            await interaction.followup.send(
                f"{poll['question']}\n\n*(Nach der Abstimmung kannst du diese Nachricht verwerfen. Wenn die Abstimmung "
                f"nicht funktioniert, bitte verwirf die Nachricht und Klicke erneut auf den Abstimmen Button der "
                f"Abstimmung.)*", view=PollChoiceView(poll, interaction.user, interaction.message, self.polls),
                ephemeral=True)

    @discord.ui.button(label='Teilnehmer', style=discord.ButtonStyle.blurple, custom_id='poll_view:participants',
                       emoji="👥")
    async def participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if poll := self.polls.polls.get(str(interaction.message.id)):
            if poll["anonymous"]:
                await interaction.followup.send(
                    "Diese Umfrage ist anonym. Daher kann ich dir nicht sagen, wer an dieser  Umfrage teilgenommen hat.")
            else:
                await show_participants(interaction, poll, ephemeral=True)

    @discord.ui.button(label='Beenden', style=discord.ButtonStyle.gray, custom_id='poll_view:close', emoji="🛑")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if poll := self.polls.polls.get(str(interaction.message.id)):
            if poll.get("author") == interaction.user.id or utils.is_mod(interaction.user):
                if not poll["anonymous"]:
                    await show_participants(interaction, poll, ephemeral=False)

                del self.polls.polls[str(interaction.message.id)]
                self.polls.save()

                await interaction.edit_original_response(view=None)

    @discord.ui.button(label='Löschen', style=discord.ButtonStyle.gray, custom_id='poll_view:delete', emoji="🗑")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if poll := self.polls.polls.get(str(interaction.message.id)):
            if poll.get("author") == interaction.user.id or utils.is_mod(interaction.user):
                await interaction.followup.send(f"Umfrage {poll.get('question')} gelöscht.", ephemeral=True)
                await interaction.message.delete()
                del self.polls[str(interaction.message.id)]
                self.polls.save()


class PollChoiceView(discord.ui.View):
    def __init__(self, poll, user, message, polls):
        super().__init__(timeout=None)
        self.poll = poll
        self.user = user
        self.add_item(PollDropdown(poll, user, message, polls))


class PollDropdown(discord.ui.Select):
    def __init__(self, poll, user, message, polls):
        self.poll = poll
        self.user = user
        self.message = message
        self.polls = polls
        participant = self.poll["participants"].get(str(user.id))
        options = [discord.SelectOption(label=choice[1], emoji=choice[0], value=str(idx),
                                        default=self.is_default(participant, idx)) for idx, choice in
                   enumerate(poll["choices"])]
        max_values = 1 if poll["type"] == "single" else len(options)

        super().__init__(placeholder='Gib deine Stimme(n) jetzt ab....', min_values=0, max_values=max_values,
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.poll["participants"][str(interaction.user.id)] = [int(value) for value in self.values]

        choices = [0] * len(self.poll["choices"])
        for participant in self.poll["participants"].values():
            for choice in participant:
                choices[choice] += 1

        for idx, choice in enumerate(self.poll["choices"]):
            choice[2] = choices[idx]

        await self.message.edit(embed=self.polls.get_embed(self.poll), view=PollView(self.poll))
        self.polls.save()

    def is_default(self, participant, idx):
        if participant:
            return idx in participant
        return False
