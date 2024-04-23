import asyncio
import uuid
from datetime import datetime, timedelta

from discord import app_commands, errors, Interaction
from discord.ext import tasks, commands

from models import Appointment
from views.appointment_view import AppointmentView


async def send_notification(appointment, channel):
    message = f"Benachrichtigung!\nDer Termin \"{appointment.title}\" startet "

    if appointment.reminder_sent:
        message += f"jetzt! :loudspeaker: "
    else:
        message += f"<t:{int(appointment.date_time.timestamp())}:R>."

    message += f"\n"
    message += " ".join([f"<@!{str(attendee.member_id)}>" for attendee in appointment.attendees])

    await channel.send(message)


@app_commands.guild_only()
class Appointments(commands.GroupCog, name="appointments", description="Handle Appointments in Channels"):
    def __init__(self, bot):
        self.bot = bot
        self.timer.start()

    @tasks.loop(minutes=1)
    async def timer(self):
        for appointment in Appointment.select().order_by(Appointment.channel):
            now = datetime.now()
            date_time = appointment.date_time
            remind_at = date_time - timedelta(
                minutes=appointment.reminder) if not appointment.reminder_sent else date_time

            if now >= remind_at:
                try:
                    channel = await self.bot.fetch_channel(appointment.channel)
                    message = await channel.fetch_message(appointment.message)
                    await send_notification(appointment, channel)

                    if appointment.reminder_sent:
                        await message.delete()

                        if appointment.recurring == 0:
                            appointment.delete_instance(recursive=True)
                        else:
                            new_date_time = appointment.date_time + timedelta(days=appointment.recurring)
                            reminder_sent = appointment.reminder == 0
                            Appointment.update(reminder_sent=reminder_sent, date_time=new_date_time).where(
                                Appointment.id == appointment.id).execute()
                            updated_appointment = Appointment.get(Appointment.id == appointment.id)
                            new_message = await channel.send(embed=updated_appointment.get_embed(),
                                                             view=AppointmentView())
                            Appointment.update(message=new_message.id).where(Appointment.id == appointment.id).execute()
                    else:
                        Appointment.update(reminder_sent=True).where(Appointment.id == appointment.id).execute()
                except errors.NotFound:
                    appointment.delete_instance(recursive=True)

    @timer.before_loop
    async def before_timer(self):
        await asyncio.sleep(60 - datetime.now().second)

    @app_commands.command(name="add", description="Füge dem Kanal einen neuen Termin hinzu.")
    @app_commands.describe(date="Tag des Termins im Format TT.MM.JJJJ", time="Uhrzeit des Termins im Format HH:MM",
                           reminder="Wie viele Minuten bevor der Termin startet, soll eine Erinnerung verschickt werden?",
                           title="Titel des Termins (so wie er dann evtl. auch im Kalender steht).",
                           description="Detailliertere Beschreibung, was gemacht werden soll.",
                           recurring="In welchem Intervall (in Tagen) soll der Termin wiederholt werden?")
    async def cmd_add_appointment(self, interaction: Interaction, date: str, time: str, reminder: int, title: str,
                                  description: str = "", recurring: int = 0):
        """ Add an appointment to a channel """
        channel = interaction.channel
        author_id = interaction.user.id
        try:
            date_time = datetime.strptime(f"{date} {time}", self.bot.dt_format())
        except ValueError:
            await channel.send("Fehler! Ungültiges Datums und/oder Zeit Format!")
            return

        appointment = Appointment.create(channel=channel.id, message=0, date_time=date_time, reminder=reminder,
                                         title=title, description=description, author=author_id, recurring=recurring,
                                         reminder_sent=reminder == 0, uuid=uuid.uuid4())

        await interaction.response.send_message(embed=appointment.get_embed(), view=AppointmentView())
        message = await interaction.original_response()
        Appointment.update(message=message.id).where(Appointment.id == appointment.id).execute()

    @app_commands.command(name="list", description="Listet alle Termine dieses Kanals auf.")
    @app_commands.describe(show_all="Zeige die Liste für alle an.")
    async def cmd_appointments_list(self, interaction: Interaction, show_all: bool = False):
        """ List (and link) all Appointments in the current channel """
        await interaction.response.defer(ephemeral=not show_all)

        appointments = Appointment.select().where(Appointment.channel == interaction.channel_id)
        if appointments:
            answer = f'Termine dieses Channels:\n'

            for appointment in appointments:
                try:
                    message = await interaction.channel.fetch_message(appointment.message)
                    answer += f'<t:{int(appointment.date_time.timestamp())}:F>: {appointment.title} => ' \
                              f'{message.jump_url}\n'
                except errors.NotFound:
                    appointment.delete_instance(recursive=True)

            await interaction.edit_original_response(content=answer)
        else:
            await interaction.edit_original_response(content="Für diesen Channel existieren derzeit keine Termine")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Appointments(bot))
    bot.add_view(AppointmentView())