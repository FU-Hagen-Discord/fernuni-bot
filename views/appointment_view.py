from datetime import timedelta

import discord
from discord import File

import utils
from models import Appointment, Attendee


class AppointmentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Zusagen', style=discord.ButtonStyle.green, custom_id='appointment_view:accept', emoji="👍")
    async def on_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if attendee := appointment.attendees.filter(member_id=interaction.user.id):
                await interaction.response.send_message("Du bist bereits Teilnehmerin dieses Termins.",
                                                        ephemeral=True)
                return
            else:
                Attendee.create(appointment=appointment.id, member_id=interaction.user.id)
                await interaction.message.edit(embed=appointment.get_embed())

        await interaction.response.defer(thinking=False)

    @discord.ui.button(label='Absagen', style=discord.ButtonStyle.red, custom_id='appointment_view:decline', emoji="👎")
    async def on_decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if attendee := appointment.attendees.filter(member_id=interaction.user.id):
                attendee = attendee[0]
                attendee.delete_instance()
                await interaction.message.edit(embed=appointment.get_embed())
            else:
                await interaction.response.send_message("Du kannst nur absagen, wenn du vorher zugesagt hast.",
                                                        ephemeral=True)
                return

        await interaction.response.defer(thinking=False)

    @discord.ui.button(label='Übersringen', style=discord.ButtonStyle.blurple, custom_id='appointment_view:skip',
                       emoji="⏭️")
    async def on_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if interaction.user.id == appointment.author or utils.is_mod(interaction.user):
                new_date_time = appointment.date_time + timedelta(days=appointment.recurring)
                Appointment.update(date_time=new_date_time, reminder_sent=False).where(
                    Appointment.id == appointment.id).execute()
                updated_appointment = Appointment.get(Appointment.id == appointment.id)
                await interaction.message.edit(embed=updated_appointment.get_embed())


    @discord.ui.button(label='Download .ics', style=discord.ButtonStyle.blurple, custom_id='appointment_view:ics',
                       emoji="📅")
    async def on_ics(self, interaction: discord.Interaction, button: discord.ui.Button):
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            await interaction.response.send_message("", file=File(appointment.get_ics_file(),
                                                                  filename=f"{appointment.title}.ics"), ephemeral=True)

    @discord.ui.button(label='Löschen', style=discord.ButtonStyle.gray, custom_id='appointment_view:delete', emoji="🗑")
    async def on_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if interaction.user.id == appointment.author or utils.is_mod(interaction.user):
                appointment.delete_instance(recursive=True)
                await interaction.message.delete()
