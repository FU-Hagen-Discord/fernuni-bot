from datetime import timedelta

import discord
from discord import File

import utils
from models import Appointment, Attendee


class AppointmentView(discord.ui.View):
    def __init__(self, can_skip: bool):
        super().__init__(timeout=None)
        self.on_skip.disabled = not can_skip

    @discord.ui.button(label='Anmelden', style=discord.ButtonStyle.green, custom_id='appointment_view:accept', emoji="👍")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.reactivate_buttons('appointment_view:decline')        
        
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            attendee = appointment.attendees.filter(member_id=interaction.user.id)
            button.disabled = True
            if attendee:
                await interaction.response.send_message("Du bist bereits Teilnehmerin dieses Termins.",
                                                        ephemeral=True, view=self)
                return
            else:
                Attendee.create(appointment=appointment.id, member_id=interaction.user.id)
                await interaction.message.edit(
                    embed=appointment.get_embed(1 if appointment.reminder_sent and appointment.reminder > 0 else 0), view=self)
        await interaction.response.defer(thinking=False)

    @discord.ui.button(label='Abmelden', style=discord.ButtonStyle.red, custom_id='appointment_view:decline', emoji="👎")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.reactivate_buttons('appointment_view:accept')                         
                
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            attendee = appointment.attendees.filter(member_id=interaction.user.id)
            button.disabled = True
            if attendee:
                attendee = attendee[0]
                attendee.delete_instance()
                
                await interaction.message.edit(
                    embed=appointment.get_embed(1 if appointment.reminder_sent and appointment.reminder > 0 else 0), view=self)
            else:
                await interaction.response.send_message("Du kannst nur absagen, wenn du vorher zugesagt hast.",
                                                        ephemeral=True, view=self)
                return

        await interaction.response.defer(thinking=False)

    @discord.ui.button(label='Überspringen', style=discord.ButtonStyle.blurple, custom_id='appointment_view:skip',
                       emoji="⏭️")
    async def on_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if interaction.user.id == appointment.author or utils.is_mod(interaction.user):
                new_date_time = appointment.date_time + timedelta(days=appointment.recurring)
                Appointment.update(date_time=new_date_time, reminder_sent=False).where(
                    Appointment.id == appointment.id).execute()
                updated_appointment = Appointment.get(Appointment.id == appointment.id)
                
                await interaction.message.edit(embed=updated_appointment.get_embed(
                    1 if updated_appointment.reminder_sent and updated_appointment.reminder > 0 else 0))                

    @discord.ui.button(label='Download .ics', style=discord.ButtonStyle.blurple, custom_id='appointment_view:ics',
                       emoji="📅")
    async def ics(self, interaction: discord.Interaction, button: discord.ui.Button):
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            await interaction.response.send_message("", file=File(appointment.get_ics_file(),
                                                                  filename=f"{appointment.title}_{appointment.uuid}.ics"), ephemeral=True)

    @discord.ui.button(label='Löschen', style=discord.ButtonStyle.gray, custom_id='appointment_view:delete', emoji="🗑")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=False)
        if appointment := Appointment.get_or_none(Appointment.message == interaction.message.id):
            if interaction.user.id == appointment.author:
                appointment.delete_instance(recursive=True)
                await interaction.message.delete()
                
    def reactivate_buttons(self, opposite_button_id: str):
        for child in self.children:
            can_edit = child.custom_id == opposite_button_id and child.custom_id != 'appointment_view:skip'
            if isinstance(child, discord.ui.Button) and can_edit:
                child.disabled = False
                