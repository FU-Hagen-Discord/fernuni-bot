import io
from datetime import datetime

import discord
from discord import File

import utils


def get_ics_file(title, date_time, reminder, recurring, description, ics_uuid):
    fmt = "%Y%m%dT%H%M"
    appointment = f"BEGIN:VCALENDAR\n" \
                  f"PRODID:Boty McBotface\n" \
                  f"VERSION:2.0\n" \
                  f"BEGIN:VTIMEZONE\n" \
                  f"TZID:Europe/Berlin\n" \
                  f"BEGIN:DAYLIGHT\n" \
                  f"TZOFFSETFROM:+0100\n" \
                  f"TZOFFSETTO:+0200\n" \
                  f"TZNAME:CEST\n" \
                  f"DTSTART:19700329T020000\n" \
                  f"RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3\n" \
                  f"END:DAYLIGHT\n" \
                  f"BEGIN:STANDARD\n" \
                  f"TZOFFSETFROM:+0200\n" \
                  f"TZOFFSETTO:+0100\n" \
                  f"TZNAME:CET\n" \
                  f"DTSTART:19701025T030000\n" \
                  f"RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10\n" \
                  f"END:STANDARD\n" \
                  f"END:VTIMEZONE\n" \
                  f"BEGIN:VEVENT\n" \
                  f"DTSTAMP:{datetime.now().strftime(fmt)}00Z\n" \
                  f"UID:{ics_uuid}\n" \
                  f"SUMMARY:{title}\n"
    appointment += f"RRULE:FREQ=DAILY;INTERVAL={recurring}\n" if recurring else f""
    appointment += f"DTSTART;TZID=Europe/Berlin:{date_time.strftime(fmt)}00\n" \
                   f"DTEND;TZID=Europe/Berlin:{date_time.strftime(fmt)}00\n" \
                   f"TRANSP:OPAQUE\n" \
                   f"BEGIN:VALARM\n" \
                   f"ACTION:DISPLAY\n" \
                   f"TRIGGER;VALUE=DURATION:-PT{reminder}M\n" \
                   f"DESCRIPTION:{description}\n" \
                   f"END:VALARM\n" \
                   f"END:VEVENT\n" \
                   f"END:VCALENDAR"
    ics_file = io.BytesIO(appointment.encode("utf-8"))
    return ics_file


class AppointmentView(discord.ui.View):
    def __init__(self, appointments):
        super().__init__(timeout=None)
        self.appointments = appointments

    @discord.ui.button(label='Zusagen', style=discord.ButtonStyle.green, custom_id='appointment_view:accept', emoji="👍")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if channel_appointments := self.appointments.appointments.get(str(interaction.channel_id)):
            if appointment := channel_appointments.get(str(interaction.message.id)):
                if attendees := appointment.get("attendees"):
                    attendees[str(interaction.user.id)] = 1
                    self.appointments.save_appointments()
                    await self.update_appointment(interaction.message, appointment)

    @discord.ui.button(label='Absagen', style=discord.ButtonStyle.red, custom_id='appointment_view:decline', emoji="👎")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if channel_appointments := self.appointments.appointments.get(str(interaction.channel_id)):
            if appointment := channel_appointments.get(str(interaction.message.id)):
                if attendees := appointment.get("attendees"):
                    if attendees.get(str(interaction.user.id)):
                        del attendees[str(interaction.user.id)]
                        self.appointments.save_appointments()
                        await self.update_appointment(interaction.message, appointment)

    @discord.ui.button(label='Download .ics', style=discord.ButtonStyle.blurple, custom_id='appointment_view:ics',
                       emoji="📅")
    async def ics(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if channel_appointments := self.appointments.appointments.get(str(interaction.channel_id)):
            if appointment := channel_appointments.get(str(interaction.message.id)):
                title = appointment.get("title")
                date_time = datetime.strptime(appointment.get("date_time"), self.appointments.fmt)
                reminder = appointment.get("reminder")
                recurring = appointment.get("recurring")
                description = appointment.get("description")
                ics_uuid = appointment.get("ics_uuid")
                file = File(get_ics_file(title, date_time, reminder, recurring, description, ics_uuid),
                            filename=f"{appointment.get('title')}_{appointment.get('ics_uuid')}.ics")
                await interaction.followup.send(file=file, ephemeral=True)

    @discord.ui.button(label='Löschen', style=discord.ButtonStyle.gray, custom_id='appointment_view:delete', emoji="🗑")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if channel_appointments := self.appointments.appointments.get(str(interaction.channel_id)):
            if appointment := channel_appointments.get(str(interaction.message.id)):
                if appointment.get("author_id") == interaction.user.id or utils.is_mod(interaction.user):
                    await interaction.followup.send(f"Termin {appointment.get('title')} gelöscht.", ephemeral=True)
                    await interaction.message.delete()
                    del channel_appointments[str(interaction.message.id)]
                    self.appointments.save_appointments()

    async def update_appointment(self, message, appointment):
        channel = message.channel
        message = message
        author_id = appointment.get("author_id")
        description = appointment.get("description")
        title = appointment.get("title")
        date_time = datetime.strptime(appointment.get("date_time"), self.appointments.fmt)
        reminder = appointment.get("reminder")
        recurring = appointment.get("recurring")
        attendees = appointment.get("attendees")

        await self.appointments.send_or_update_appointment(channel, author_id, description, title, date_time, reminder,
                                                           recurring, attendees, message=message)
