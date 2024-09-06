

import firebase_admin
from firebase_admin import credentials, db
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('TOKEN')

CLIENT_ID = os.getenv('CLIENT_ID')
REDIRECT_URI = os.getenv('REDIRECT_URI')

cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})

users_ref = db.reference('users')

def get_user(user_id):
    user = users_ref.child(user_id).get()
    if user:
        return user
    else:
        return None

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)


available_times = ['17:00', '18:00', '19:00']
available_sports = ['football', 'volleyball', 'handball', 'basketball']
reservations = {}


def is_valid_time(time):
    return time in available_times

def is_valid_sport(sport):
    return sport in available_sports

def parse_date(date_str):
    try:
        date_str = date_str.strip('/')
        return datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError:
        return None

def is_date_within_range(date_obj):
    today = datetime.now().date()
    end_date = today + timedelta(days=7)
    return today <= date_obj.date() <= end_date

def get_reservation_key(date, time, sport):
    return f"{date}_{time}_{sport}"

async def send_error(interaction, message):
    await interaction.response.send_message(message, ephemeral=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(synced)
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="reserve", description="Reserve a spot")
@app_commands.describe(date="The date of reservation (YYYY/MM/DD)", time="The time of reservation", sport="The sport to reserve")
async def reserve_command(interaction: discord.Interaction, date: str, time: str, sport: str):
    if(not get_user(str(interaction.user.id))):
        await send_error(interaction, "Please sign in to 42 first using the `/sing_in` command.")
        return
    sport = sport.lower()
    date_obj = parse_date(date)
    if not date_obj:
        await send_error(interaction, "Invalid date format. Please use YYYY/MM/DD.")
        return

    if not is_date_within_range(date_obj):
        await send_error(interaction, "Invalid date. Please choose a date between today and a week from now.")
        return

    if not is_valid_time(time):
        await send_error(interaction, "Invalid time. Please choose a time from 17:00, 18:00, or 19:00.")
        return

    if time < "17:00" or time > "19:00":
        await send_error(interaction, "Invalid time. Please choose a time from 17:00, 18:00, or 19:00.")
        return

    if not is_valid_sport(sport):
        await send_error(interaction, "Invalid sport. Please choose from football, volleyball, handball, and basketball.")
        return

    reservation_key = get_reservation_key(date_obj.date(), time, sport)
    if reservation_key in reservations:
        await send_error(interaction, f"Time slot {date} {time} for {sport} is already reserved.")
        return

    reservations[reservation_key] = interaction.user.mention
    await interaction.response.send_message(f"Reserved {date} {time} for {sport} for {interaction.user.mention}!", ephemeral=True)

@bot.tree.command(name="cancel", description="Cancel a reservation")
@app_commands.describe(date="The date of reservation (YYYY/MM/DD)", time="The time of reservation", sport="The sport to cancel")
async def cancel_command(interaction: discord.Interaction, date: str, time: str, sport: str):
    if not get_user(str(interaction.user.id)):
        await send_error(interaction, "Please sign in to 42 first using the `/sing_in` command.")
        return

    if not (date and time and sport):
        await send_error(interaction, "Please provide date, time, and sport.")
        return

    sport = sport.lower()
    date_obj = parse_date(date)
    if not date_obj:
        await send_error(interaction, "Invalid date format. Please use YYYY/MM/DD.")
        return

    if not is_date_within_range(date_obj):
        await send_error(interaction, "Invalid date. Please choose a date between today and a week from now.")
        return

    if not is_valid_time(time):
        await send_error(interaction, "Invalid time. Please choose a time from 17:00, 18:00, or 19:00.")
        return

    if time < "17:00" or time > "19:00":
        await send_error(interaction, "Invalid time. Please choose a time from 17:00, 18:00, or 19:00.")
        return

    if not is_valid_sport(sport):
        await send_error(interaction, "Invalid sport. Please choose from football, volleyball, handball, and basketball.")
        return

    reservation_key = get_reservation_key(date_obj.date(), time, sport)

    if reservation_key not in reservations or interaction.user.mention != reservations[reservation_key]:
        await send_error(interaction, f"You don't have a reservation for {date} {time} for {sport}.")
        return

    del reservations[reservation_key]
    await interaction.response.send_message(f"Canceled reservation for {date} {time} for {sport}.", ephemeral=True)

@bot.tree.command(name="list", description="List reservation status")
@app_commands.describe(date="The date of reservation (YYYY/MM/DD)", sport="The sport to check")
async def list_command(interaction: discord.Interaction, date: str, sport: str):
    if not (date and sport):
        await send_error(interaction, "Please provide date and sport.")
        return
    sport = sport.lower()
    date_obj = parse_date(date)
    if not date_obj:
        await send_error(interaction, "Invalid date format. Please use YYYY/MM/DD.")
        return

    if not is_date_within_range(date_obj):
        await send_error(interaction, "Invalid date. Please choose a date between today and a week from now.")
        return

    if not is_valid_sport(sport):
        await send_error(interaction, "Invalid sport. Please choose from football, volleyball, handball, and basketball.")
        return

    messages = []
    for time in available_times:
        reservation_key = get_reservation_key(date_obj.date(), time, sport)
        status = "Reserved" if reservation_key in reservations else "Not Reserved"
        messages.append(f"Time: **{time}** - Status: **{status}**")

    embed = discord.Embed(
        title="Reservation Status",
        description=f"Date: **{date}**\nSport: **{sport}**\n\n" + "\n".join(messages),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed , ephemeral=True)

@bot.tree.command(name="sing_in", description="Sign in to out Lak server")
async def sing_in_command(interaction: discord.Interaction):
    if get_user(str(interaction.user.id)):
        await send_error(interaction, "You are already signed in.")
        return
    user_info = str(interaction.user.id) +"$"+  interaction.user.name
    oauth_url = (
        f"https://api.intra.42.fr/oauth/authorize?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"state={user_info}&"
    )
    embed = discord.Embed(
        title="Sign in to 42",
        description="Please click the link below to sign in to 42. This will redirect you to your 42 account.",
        color=discord.Color.blue()
    )
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Sign in", value=f"[Click here]({oauth_url})")
    await interaction.response.send_message(embed=embed , ephemeral=True)

@bot.tree.command(name="help", description="Get help")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help",
        description="Here are the available commands:",
        color=discord.Color.blue()
    )
    for command in bot.tree.get_commands():
        embed.add_field(name=command.name, value=command.description, inline=False)
    await interaction.response.send_message(embed=embed , ephemeral=True)

bot.run(TOKEN)