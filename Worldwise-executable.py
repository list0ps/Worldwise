import discord
import aiohttp
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from pathlib import Path
import asyncio  # Import asyncio for background tasks
import pytz  # Adding this for timezone handling
import time
start_time = time.time()
from discord import app_commands
from datetime import datetime  # Adding this for date and time handling
from data_mappings import (
    timezones_dict,
    USER_TIMEZONE_MAPPING,
    CURRENCY_NAMES,
    COUNTRY_ABBREVIATIONS,
    SUPPORTED_CURRENCIES,
    USER_LOCATION_MAPPING,
)
from readme_content import sections
from readme_content import (
    get_weather_help_embed,
    get_currency_help_embed,
    get_time_help_embed,
    get_currency_list_embed,
    get_timezone_list_embed
)

from datetime import datetime

#change

from dotenv import load_dotenv
load_dotenv()

import os
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


command_counter = 0
active_users = set()

def log_command_to_file(user, content, guild=None, channel=None):
    log_file = "chat_logs.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guild_name = guild.name if guild else "DM"
    channel_name = channel.name if channel else "DM"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{guild_name}#{channel_name}] {user}: {content}\n")



# Function to build an embed from a section
def build_embed(section):
    embed = discord.Embed(
        title=section["title"],
        description=section["description"],
        color=section["color"]
    )
    for field in section["fields"]:
        embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
    return embed

class HelpView(discord.ui.View):
    def __init__(self, current_page, total_pages):
        super().__init__()
        self.current_page = current_page
        self.total_pages = total_pages

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            embed = build_embed(sections[self.current_page])
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            embed = build_embed(sections[self.current_page])
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(placeholder="Select a section", options=[
        discord.SelectOption(label=section["title"], value=str(index))
        for index, section in enumerate(sections)
    ])
    async def select_section(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_value = select.values[0]  # This is now correct
        self.current_page = int(selected_value)
        embed = build_embed(sections[self.current_page])
        await interaction.response.edit_message(embed=embed, view=self)

DESC_FILE = Path("user_descriptions.json")

def load_descriptions():
    if DESC_FILE.exists():
        with open(DESC_FILE, "r") as f:
            return json.load(f)
    return {}

def save_descriptions(data):
    with open(DESC_FILE, "w") as f:
        json.dump(data, f, indent=2)

#web scrapper bs from chatgpt to fetch conversion info 
def get_exchange_rate(from_currency, to_currency):
    url = f"https://wise.com/us/currency-converter/{from_currency.lower()}-to-{to_currency.lower()}-rate?amount=1000"
    response = requests.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract the exchange rate
        rate_text = soup.find('span', class_='text-success')
        rate = float(re.search(r"\d+\.\d+", rate_text.text.strip()).group()) if rate_text else None

        # Extract the 30-day high, low, average, and change
        table_rows = soup.select('table tr')
        high_30 = float(table_rows[1].find_all('td')[1].text)
        low_30 = float(table_rows[2].find_all('td')[1].text)
        average_30 = float(table_rows[3].find_all('td')[1].text)
        change_30 = table_rows[4].find_all('td')[1].text.strip()
        
        return rate, high_30, low_30, average_30, change_30, url
    else:
        print(f"Failed to retrieve page. Status code: {response.status_code}")
        return None, None, None, None, None, None
    
    
# Updated get_current_time function with additional cities for more countries
def get_current_time(location):
    # Dictionary of countries, abbreviations, cities and GMT offsets
    # Only way to support country abbreviations was to list them as separate elements (because I suck at python)
 

    # Normalizing input for case-insensitive matching because my friend alex is weird
    location = location.strip().casefold()

    results = []

    # Check if location is a country or abbreviation 
    if location in timezones_dict:
        for city, abbreviation, timezone, gmt_offset in timezones_dict[location]:
            tz = pytz.timezone(timezone)
            city_time = datetime.now(tz)
            results.append(f"The current time is **{city_time.strftime('%I:%M %p')}** in {city.title()}, {location.upper()}. {gmt_offset}")
        return results

    # Check for a matching city or abbreviation
    for country, cities in timezones_dict.items():
        for city, abbreviation, timezone, gmt_offset in cities:
            if location in {city, abbreviation}:
                tz = pytz.timezone(timezone)
                city_time = datetime.now(tz)
                results.append(f"The current time is **{city_time.strftime('%I:%M %p')}** in {city.title()}, {country.upper()}. {gmt_offset}")
                return results

    return None


# Updated `convert_time` function for accurate conversions, was broken because misalignment of full names
def convert_time(time_str, from_location, to_location):
    # Uses the same `timezones_dict` as in get_current_time

    # Normalizing inputs for case-insensitive matching
    from_location = from_location.strip().casefold()
    to_location = to_location.strip().casefold()

    # Gathering entries for source and destination locations
    from_entries = [entry for country, cities in timezones_dict.items() for entry in cities if from_location in {country, entry[0], entry[1]}]
    to_entries = [entry for country, cities in timezones_dict.items() for entry in cities if to_location in {country, entry[0], entry[1]}]

    if not from_entries or not to_entries:
        return [f"**Error:** Could not find timezone information for one of the locations."]

    converted_times = []
    
    # Group destination cities by timezone
    cities_by_timezone = {}
    for to_city, _, to_tz, gmt_offset in to_entries:
        if to_tz not in cities_by_timezone:
            cities_by_timezone[to_tz] = []
        cities_by_timezone[to_tz].append((to_city, gmt_offset))

    for from_city, _, from_tz, _ in from_entries:
        tz = pytz.timezone(from_tz)
        current_date = datetime.now()  # Get current date

        # Parse the input time
        time_str = time_str.strip().lower()

        # Check if time is in 12-hour or 24-hour format and parse accordingly
        if 'am' in time_str or 'pm' in time_str:  # 12-hour format
            try:
                naive_time = datetime.strptime(time_str, "%I:%M%p")  # 5:34pm
            except ValueError:
                naive_time = datetime.strptime(time_str, "%I%p")  # 5pm
        else:  # 24-hour format (e.g., 17:00, 1700)
            try:
                naive_time = datetime.strptime(time_str, "%H:%M")  # 17:00
            except ValueError:
                naive_time = datetime.strptime(time_str, "%H%M")  # 1700

        # Replacing current date to preserve year, month, day while parsing time
        naive_time = naive_time.replace(year=current_date.year, month=current_date.month, day=current_date.day)

        aware_time = tz.localize(naive_time)  # Localize to source timezone

        for to_tz, cities in cities_by_timezone.items():
            # Only take the first city from each timezone group
            to_city, gmt_offset = cities[0]
            target_tz = pytz.timezone(to_tz)
            converted_time = aware_time.astimezone(target_tz)  # Convert to target timezone

            # Format the time in HH:MM format (24-hour time) for consistency
            from_time = aware_time.strftime('%H:%M')  # Always format 24-hour time as HH:MM
            to_time = converted_time.strftime('%H:%M')  # Always format 24-hour time as HH:MM

            # Check if the original time format was 12-hour (contains 'am' or 'pm')
            if 'am' in time_str or 'pm' in time_str:
                # If the time was in 12-hour format, respond in 12-hour format
                from_time = format_time(aware_time, format_12hr=True)
                to_time = format_time(converted_time, format_12hr=True)
            else:
                # If the time was in 24-hour format, keep the 24-hour format
                from_time = format_time(aware_time, format_12hr=False)
                to_time = format_time(converted_time, format_12hr=False)

            converted_times.append(f"**{from_time}** in {from_city.title()} is **{to_time}** in {to_city.title()}, {gmt_offset}")

    return list(set(converted_times))  # Remove duplicates


# Function to format a time object to 12-hour or 24-hour time
def format_time(time_obj, format_12hr=True):
    """Formats a datetime object into 12-hour or 24-hour format string."""
    if format_12hr:
        return time_obj.strftime('%I:%M%p').lower()  # Convert to 12-hour format (AM/PM)
    else:
        return time_obj.strftime('%H:%M')  # Convert to 24-hour format


TEST_GUILD_ID = 1356960708230779023
# Initialize Discord bot with intents - probably should've been at the very top 
# Also this was introduced in 2023 most likely, wasn't required for discord.py
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True  # Make sure this is enabled
client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)
test_guild = discord.Object(id=TEST_GUILD_ID)

descriptions = load_descriptions()



# Placeholder for error logging channel and startup message channel
ERROR_CHANNEL_ID = 1357709109071184093  # error logs
STARTUP_CHANNEL_ID = 1357709085184884766  # channel ID for startup messages
PERIODIC_CHANNEL_ID = 1358254137946542283  # spams 28m so heroku doesn't bonk us

# startup message
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    # Change the bot's presence
    await client.change_presence(activity=discord.Game(name='time and money.'))

    # Send a startup message to the designated channel
    startup_channel = client.get_channel(STARTUP_CHANNEL_ID)
    if startup_channel:
        await startup_channel.send("I am now online.")


       # await tree.sync(guild=test_guild) #kept for testing
   # print("Synced slash commands to test guild.")
        await tree.sync()  # Sync globally
    print("Synced slash commands globally.")

    
    # Start background task for periodic messages so Heroku doesn't go bonkers
    #client.loop.create_task(send_periodic_message())


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.guild:
        global command_counter
    command_counter += 1
    active_users.add(str(message.author))
    log_command_to_file(str(message.author), message.content, message.guild, message.channel)


    # Write stats
    with open("bot_stats.json", "w") as f:
        json.dump({
            "guilds": len(client.guilds),
            "commands_today": command_counter,
            "active_users": len(active_users),
            "updated": datetime.now().isoformat()
        }, f)


    # DM forwarding, sends any content (text or attachments) sent to bot's DM - to specified channel  
  # Check if the message is in a DM (Direct Message)
    if isinstance(message.channel, discord.DMChannel):
        target_channel = client.get_channel(1306617117528952955)  # Replace with the target channel ID

        # Check if the target channel exists
        if target_channel:
            # Send the content of the DM (if there's any text)
            embed = discord.Embed(
                title="New DM Received",
                description=message.content if message.content else "[No Text]",
                color=discord.Color.dark_teal()  # Use a green color for DM notifications
            )
            embed.add_field(name="From", value=f"{message.author} (ID: {message.author.id})", inline=False)
            
            # Forward the message embed to the target channel
            await target_channel.send(embed=embed)

            # Forward any attachments (images, files)
            if message.attachments:
                for attachment in message.attachments:
                    await target_channel.send(f"Attachment: {attachment.url}")
        else:
            print("Target channel not found.")

# Admin-only commands



    # if message.content.lower().startswith("whelp"):
    #     current_page = 0
    #     total_pages = len(sections)

    #     # Create the initial embed
    #     embed = build_embed(sections[current_page])  # Use the new function name
    #     view = HelpView(current_page, total_pages)
    #     await message.channel.send(embed=embed, view=view)

    # # Handle translate command
    # if message.content.lower().startswith('translate '):
    #     # Extract the text to translate (everything after 'translate ')
    #     text_to_translate = message.content[10:].strip()
        
    #     if not text_to_translate:
    #         await message.channel.send("Please provide some text to translate.")
    #         return
            
    #     try:
    #         # Create URL for Google Translate
    #         url = f"https://translate.google.com/m?sl=auto&tl=en&q={text_to_translate}"
            
    #         # Send request and get response
    #         headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    #         response = requests.get(url, headers=headers)
            
    #         if response.status_code == 200:
    #             # Parse the response
    #             soup = BeautifulSoup(response.text, 'html.parser')
    #             # Find the translation result
    #             result = soup.find('div', {'class': 'result-container'})
                
    #             if result:
    #                 translated_text = result.text
    #                 await message.channel.send(f"**Translation:**\n{translated_text}")
    #             else:
    #                 await message.channel.send("Sorry, I couldn't translate that text.")
    #         else:
    #             await message.channel.send("Sorry, there was an error accessing the translation service.")
                
    #     except Exception as e:
    #         error_channel = client.get_channel(ERROR_CHANNEL_ID)
    #         if error_channel:
    #             await error_channel.send(f"Translation error: {str(e)}")
    #         await message.channel.send("Sorry, there was an error processing your translation request.")


    # # memlist command
    # if message.content.lower() == 'mlist':
    #     # Check if the user has permission
    #     #if message.author.id != 340485392434200576:
    #     #    await message.channel.send("You do not have permission to use this command.")
    #     #    return

    #     guild = message.guild  # Get the guild (server) where the message was sent
        
    #     # Create a list to hold member names and join dates
    #     member_list = []
        
    #     # Fetch all members using an async for loop
    #     async for member in guild.fetch_members():
    #         # Use nickname if available, otherwise use username
    #         nickname = member.nick if member.nick else member.name
            
    #         # Format the join date with shortened month names
    #         join_date = member.joined_at.strftime('%b %d, %Y') if member.joined_at else 'N/A'
    #         member_list.append((nickname, join_date, member.joined_at))  # Store join date for sorting

    #     # Sort members by join date (oldest first)
    #     member_list.sort(key=lambda x: x[2])  # Sort by the actual join date

    #     # Create a formatted string with bullet numbers
    #     formatted_member_list = "\n".join(f"{i + 1}. {nickname} [{join_date}]" for i, (nickname, join_date, _) in enumerate(member_list))

    #     # Create an embed for the response with dark red color
    #     embed = discord.Embed(
    #         title="Members in this server",
    #         description="Member | When they joined the server\n" + formatted_member_list,  # Added clarification
    #         color=discord.Color.dark_red()  # Change color to dark red
    #     )

    #     # Send the embed in the channel
    #     await message.channel.send(embed=embed)

    

    # Check if the message content is the trigger for listing join dates
    # if message.content.lower() == 'jdlist':
    #     # Check if the user has permission
    #     #if message.author.id != 340485392434200576:
    #     #    await message.channel.send("You do not have permission to use this command.")
    #     #    return

    #     guild = message.guild  # Get the guild (server) where the message was sent
        
    #     # Create a list to hold member names and account creation dates
    #     account_list = []
        
    #     # Fetch all members using an async for loop
    #     async for member in guild.fetch_members():
    #         # Use nickname if available, otherwise use username
    #         nickname = member.nick if member.nick else member.name
            
    #         # Format the account creation date with shortened month names
    #         account_creation_date = member.created_at.strftime('%b %d, %Y') if member.created_at else 'N/A'
    #         account_list.append((nickname, account_creation_date, member.created_at))  # Store nickname, account creation date, and actual date

    #     # Sort members by account creation date (oldest first)
    #     account_list.sort(key=lambda x: x[2])  # Sort by the actual account creation date

    #     # Create a formatted string with bullet numbers
    #     formatted_account_list = "\n".join(f"{i + 1}. {nickname} [{account_creation_date}]" for i, (nickname, account_creation_date, _) in enumerate(account_list))

    #     # Create an embed for the response with dark red color
    #     embed = discord.Embed(
    #         title="Members' Account Creation Dates",
    #         description=formatted_account_list,
    #         color=discord.Color.dark_red()  # Change color to dark red
    #     )

    #     # Send the embed in the channel
    #     await message.channel.send(embed=embed)


# weather stuff
    # if message.content.lower().startswith('weather'):
    #     # Get the content after 'weather'
    #     query = message.content[7:].strip()
        
    #     if not query:
    #         await message.channel.send("Please provide a location or mention a user. Example: weather London,UK or weather @username")
    #         return

    #     # Check if it's a user mention
    #     if query.startswith('<@') and query.endswith('>'):
    #         # Extract user ID from mention
    #         user_id = query[2:-1]  # Remove <@ and >
    #         if user_id.startswith('!'): # Handle nicknames
    #             user_id = user_id[1:]
            
    #         # Look up user's location in mapping
    #         if user_id in USER_LOCATION_MAPPING:
    #             username, location = USER_LOCATION_MAPPING[user_id]
    #         else:
    #             await message.channel.send("This user's location isn't registered in my database.")
    #             return
    #     else:
    #         # Use the provided location directly
    #         location = query

    #     try:
    #         async with aiohttp.ClientSession() as session:
    #             # Get coordinates for location
    #             geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={WEATHER_API_KEY}"
    #             async with session.get(geocoding_url) as response:
    #                 if response.status != 200:
    #                     await message.channel.send("Sorry, I couldn't find that location.")
    #                     return
                    
    #                 geocode_data = await response.json()
    #                 if not geocode_data:
    #                     await message.channel.send("Sorry, I couldn't find that location.")
    #                     return

    #                 lat = geocode_data[0]['lat']
    #                 lon = geocode_data[0]['lon']
    #                 location_name = geocode_data[0]['name']
    #                 country = geocode_data[0]['country']

    #             # Get weather data
    #             weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
    #             async with session.get(weather_url) as response:
    #                 if response.status != 200:
    #                     await message.channel.send("Sorry, I couldn't fetch the weather data.")
    #                     return
                    
    #                 weather_data = await response.json()

    #         # Extract weather information
    #         temperature = round(weather_data['main']['temp'])
    #         condition = weather_data['weather'][0]['description']
    #         temp_max = round(weather_data['main']['temp_max'])
    #         temp_min = round(weather_data['main']['temp_min'])

    #         # Prepare weather message
    #         if query.startswith('<@'):
    #             # If it was a user mention, include their username
    #             weather_message = (
    #                 f"For **{username}**, it's **{condition}** and **{temperature} °C** in **{location_name}**, {country} today. "
    #                 f"They can expect highs of {temp_max} °C and lows of {temp_min} °C."
    #             )
    #         else:
    #             weather_message = (
    #                 f"It's **{condition}** and **{temperature} °C** in **{location_name}**, {country} today. "
    #                 f"Expect highs of {temp_max} °C and lows of {temp_min} °C."
    #             )
            
    #         await message.channel.send(weather_message)

    #     except Exception as e:
    #         await message.channel.send(f"An error occurred while fetching weather data: {str(e)}")    
    

    if message.content.lower().strip() == "-a uptime":
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        uptime_seconds = int(time.time() - start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        await message.channel.send(
            f"I've been online for **{hours}h {minutes}m {seconds}s**."
        )

    if message.content.lower().startswith("-a purge"):
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        parts = message.content.strip().split()

        if len(parts) != 3 or not parts[2].isdigit():
            await message.channel.send("Invalid syntax. Use `-a purge [number]`.")
            return

        count = int(parts[2])

        if not message.channel.permissions_for(message.guild.me).manage_messages:
            await message.channel.send("I don't have permission to delete messages in this channel.")
            return

        # Purge up to `count` messages before this one
        deleted = await message.channel.purge(limit=count + 1, check=lambda m: m.id != message.id)

        await message.channel.send(f"Deleted {len(deleted)} messages.")

        # Send and delete confirmation after a few seconds
        # confirm_msg = await message.channel.send(f"Deleted {len(deleted)} messages.")
        # await asyncio.sleep(5)
        # await confirm_msg.delete()

    if message.content.lower() == "-a refresh":
        if message.author.guild_permissions.administrator:
            try:
                await tree.sync(guild=message.guild)
                await message.channel.send("Slash commands have been refreshed for this server.")
            except Exception as e:
                await message.channel.send(f"Failed to refresh slash commands: {e}")
        else:
            await message.channel.send("You need to be an admin to use this command.")

    if message.content.lower() in ["-a guilds"]:
        if message.author.id != 223689629990125569: #admin ID
            await message.channel.send("You do not have permission to use this command.")
            return

        guilds = client.guilds
        if guilds:
            guild_list = "\n".join(
                [f"- **{guild.name}** (ID: {guild.id}, Members: **{guild.member_count}**)" for guild in guilds]
            )
            await message.channel.send(f"**The bot is in the following servers:**\n{guild_list}")
        else:
            await message.channel.send("**The bot is not in any servers.**")
        return
    
    if message.content.lower().startswith("-a fquit"):
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        parts = message.content.strip().split()

    # Expect exactly 3 parts: ["-a", "fquit", "<guild_id>"]
        if len(parts) != 3:
            return  # silently ignore bad format

        if not parts[2].isdigit():
            await message.channel.send("Invalid syntax. Use `-a fquit [guild_id]`.")
            return

        guild_id = int(parts[2])
        guild = discord.utils.get(client.guilds, id=guild_id)

        if guild:
            await guild.leave()
            await message.channel.send(f"✅ Left server: **{guild.name}** (ID: {guild.id})")
        else:
            await message.channel.send("Guild not found or the bot is not in that server.")

    if message.content.lower().strip() == "-a desc list":
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        data = load_descriptions()

        if not data:
            await message.channel.send("No descriptions have been set yet.")
            return

        embed = discord.Embed(
            title="Public Descriptions",
            description="Here are all saved user descriptions.",
            color=discord.Color.dark_teal()
        )

        for uid, desc in data.items():
            try:
                user = await message.guild.fetch_member(int(uid))
                embed.add_field(name=user.display_name, value=desc, inline=False)
            except:
                embed.add_field(name=f"Unknown User ({uid})", value=desc, inline=False)

        await message.channel.send(embed=embed)

    if message.content.lower().strip() == "-a desc clear":
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        save_descriptions({})
        await message.channel.send("✅ All descriptions have been cleared.")

    if message.content.lower().startswith("-a desc"):
        if message.author.id != 223689629990125569:
            return  # Silently ignore non-admins

        parts = message.content.strip().split()

        if len(parts) < 3:
            return  # Silently ignore bad input

        # Try to resolve the user
        target_user = None
        user_token = parts[2] if parts[2].isdigit() else parts[1]

        if message.mentions:
            target_user = message.mentions[0]
        elif user_token.isdigit():
            try:
                target_user = await message.guild.fetch_member(int(user_token))
            except:
                return  # Silently ignore if user ID is invalid
        else:
            return  # Silently ignore if no mention or ID

        uid = str(target_user.id)
        data = load_descriptions()

        # Reconstruct description from remaining message
        try:
            desc_start = message.content.index(user_token) + len(user_token)
            new_desc = message.content[desc_start:].strip()
        except:
            return  # Silently ignore parsing errors

        if not new_desc:
            return  # Silently ignore if no description given

        data[uid] = new_desc
        save_descriptions(data)
        await message.channel.send(f"✅ Updated description for **{target_user.display_name}**.")

    if message.content.lower().strip() == "-a shutdown":
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        await message.channel.send("Shutting down.")
        await client.close()


    if message.content.lower().startswith("-a broadcast"):
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        parts = message.content.strip().split()

        if len(parts) < 3:
            return  # not enough to proceed

        target_channel = None
        channel_arg = parts[2]

        # Try #mention first
        if message.channel_mentions:
            target_channel = message.channel_mentions[0]
        # Else try raw ID
        elif channel_arg.isdigit():
            target_channel = client.get_channel(int(channel_arg))

        if not target_channel:
            return  # silently ignore if no valid channel

        # Figure out where the message starts
        try:
            mention_text = f"<#{target_channel.id}>" if message.channel_mentions else channel_arg
            msg_start = message.content.index(mention_text) + len(mention_text)
            announcement = message.content[msg_start:].strip()
        except:
            return

        if not announcement:
            return  # silently ignore if no message to send

        try:
            await target_channel.send(announcement)
            await message.channel.send(f"✅ Announcement sent to {target_channel.mention}.")
        except discord.Forbidden:
            await message.channel.send(f"I don't have permission to send messages in {target_channel.mention}.")

    if message.content.lower().strip() == "-a role list":
        if message.author.id != 223689629990125569:
            await message.channel.send("You do not have permission to use this command.")
            return

        roles = message.guild.roles[1:]  # Exclude @everyone
        if not roles:
            await message.channel.send("No roles found in this server.")
            return

        embed = discord.Embed(
            title="📜 Role List",
            description="Each role and its assigned members",
            color=discord.Color.dark_gold()
        )

        for role in sorted(roles, key=lambda r: r.position, reverse=True):
            members = [member.display_name for member in role.members]
            if members:
                member_list = ", ".join(members[:10])
                extra = f" and {len(members) - 10} more..." if len(members) > 10 else ""
                embed.add_field(name=f"{role.name} ({len(members)})", value=member_list + extra, inline=False)

        await message.channel.send(embed=embed)

    if message.content.lower().strip() == "-a help":
        if message.author.id != 223689629990125569:
            return

        with open("admin_command_help.txt", "r", encoding="utf-8") as f:
            help_text = f.read()

        await message.channel.send(help_text)

#test

    # lists some basic server information - commented out admin restrictor for now 
    # if message.content.lower() in ["serverinfo", "svinfo"]:
    #     #if message.author.id != 340485392434200576: #admin ID
    #         #await message.channel.send("You do not have permission to use this command.")
    #         #return

    #     guild = message.guild
    #     if guild:
    #         embed = discord.Embed(title=f"Server Info for **{guild.name}**", color=discord.Color.blue())
    #         embed.add_field(name="Server ID", value=guild.id, inline=False)
    #         embed.add_field(name="Owner", value="Who knows?", inline=False)
    #         embed.add_field(name="Member Count", value=guild.member_count, inline=False)
    #         embed.add_field(name="Boost Count", value=guild.premium_subscription_count, inline=False)
    #         embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=False)
    #         embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=False)
    #         embed.add_field(name="Created At", value=guild.created_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)
            
    #         # Set server banner if available
    #         #if guild.banner:
    #         #    embed.set_image(url=guild.banner.url)

    #         # Set server icon as thumbnail if available
    #         if guild.icon:
    #             embed.set_thumbnail(url=guild.icon.url)

    #         await message.channel.send(embed=embed)
    #     else:
    #         await message.channel.send("This command must be run in a server.")


    # # Handle 'convert' or variations like 'Convert' and 'conv' (short response)
    # if message.content.lower().startswith('convert ') or message.content.lower().startswith('conv '):
    #     await handle_conversion(message, full_response=False)

    # # Handle 'convertfull' or variations like 'Convertfull' and 'convf' (full response)
    # elif message.content.lower().startswith('convertfull') or message.content.lower().startswith('convf'):
    #     await handle_conversion(message, full_response=True)

    #elif message.content.lower().startswith('wwhelp'):
        #embed = get_weather_help_embed()  # Get the weather help embed
        #await message.channel.send(embed=embed)
    
    # Handle 'chelp' for showing syntax and examples
    #elif message.content.lower().startswith('chelp'):
        #embed = get_currency_help_embed()  # Get the currency help embed
        #await message.channel.send(embed=embed)

# Adding this to the on_message handler to handle the `time` command
#    elif message.content.lower().startswith('time '):
#        await handle_time_command(message)

    # Handle 'clist' for listing supported currencies
    # elif message.content.lower().startswith('clist'):
    #     embed = get_currency_list_embed(SUPPORTED_CURRENCIES, CURRENCY_NAMES)  # Get the currency list embed
    #     await message.channel.send(embed=embed)

    # Handle 'thelp' for listing supported timezones
    #elif message.content.lower().startswith('thelp'):
        #embed = get_time_help_embed()  # Get the time help embed
        #await message.channel.send(embed=embed)
    
    # Handle 'tlist' command
    # elif message.content.lower().startswith('tlist'):
    #     embed = get_timezone_list_embed(timezones_dict, COUNTRY_ABBREVIATIONS)
    #     await message.channel.send(embed=embed)


# Handle 'time' command
#    elif message.content.lower().startswith('time '):
#        location_name = message.content[5:].strip()
#        times = get_current_time(location_name)
#        if times:
            # Capitalize only the first letter of each word in the country name
#            formatted_times = [
 #               time.replace(location_name.upper(), location_name.title()) for time in times
 #           ]
  #          await message.channel.send("\n".join(formatted_times))
   #     else:
    #        await message.channel.send(
     #           "Timezone(s) unsupported - type 'tlist' for supported timezones and cities."
      #      )

    

    
# Handle 'timec' command
  #  elif message.content.lower().startswith('timec ') or message.content.lower().startswith('timeconvert'):
  #      await handle_timec_command(message)



# function to fetch time for a specific user from user_timezone_mapping
async def handle_time_command(message):
    mentioned_users = message.mentions  # Get mentioned users

    if mentioned_users:
        responses = []

        for user in mentioned_users:
            user_data = USER_TIMEZONE_MAPPING.get(user.id)

            if not user_data:
                responses.append(f"No timezone information found for **{user.name}**.")
                continue

            username, city_abbreviation = user_data

            # Find the city, timezone, and GMT offset
            for country, cities in timezones_dict.items():
                for city, abbreviation, timezone, gmt_offset in cities:
                    if city_abbreviation == abbreviation:
                        tz = pytz.timezone(timezone)
                        city_time = datetime.now(tz)
                        formatted_time = city_time.strftime('%I:%M %p')
                        responses.append(
                            f"It's **{formatted_time}** for **{username}**, in {city.title()}, {country.title()}, {gmt_offset}."
                        )
                        break
                else:
                    continue
                break
            else:
                responses.append(f"City abbreviation `{city_abbreviation}` for **{username}** not found in timezones.")

        await message.channel.send("\n".join(responses))

    else:
        location_name = message.content[5:].strip()
        times = get_current_time(location_name)
        if times:
            formatted_times = [
                time.replace(location_name.upper(), location_name.title()) for time in times
            ]
            await message.channel.send("\n".join(formatted_times))
        else:
            await message.channel.send(
                "Timezone(s) unsupported - type 'tlist' for supported timezones and cities."
            )

# allows converting user - user time 
# fixer-upper with ye olde AI to support parsing for 24 hour format with ":"
async def handle_timec_command(message):
    parts = message.content[6:].split(' to ')
    if len(parts) == 2:
        try:
            time_str, origin_location = parts[0].rsplit(' ', 1)
            destination_location = parts[1].strip()

            mentioned_users = message.mentions
            if mentioned_users:
                if len(mentioned_users) == 2:
                    from_user, to_user = mentioned_users

                    from_user_data = USER_TIMEZONE_MAPPING.get(from_user.id)
                    to_user_data = USER_TIMEZONE_MAPPING.get(to_user.id)

                    if not from_user_data or not to_user_data:
                        await message.channel.send("Timezone information for one or both users is missing.")
                        return

                    from_username, from_city_abbreviation = from_user_data
                    to_username, to_city_abbreviation = to_user_data

                    converted_times = convert_time(time_str, from_city_abbreviation, to_city_abbreviation)

                    if converted_times:
                        # Retrieve full city names for both users
                        from_city_name = next(
                            (city.title() for country, cities in timezones_dict.items() for city, abbreviation, _, _ in cities if abbreviation == from_city_abbreviation),
                            from_city_abbreviation.upper()
                        )
                        to_city_name = next(
                            (city.title() for country, cities in timezones_dict.items() for city, abbreviation, _, _ in cities if abbreviation == to_city_abbreviation),
                            to_city_abbreviation.upper()
                        )

                        # Correct response formatting (no city repeated)
                        response = f"{time_str} for **{from_username}** in {from_city_name}, is "
                        response += f"{converted_times[0].split(' is ')[1]} for **{to_username}**."
                        await message.channel.send(response)
                        return

                    else:
                        await message.channel.send("Could not convert time between the mentioned users.")
                        return

            # If no mentions, use the location-based conversion
            converted_times = convert_time(time_str, origin_location, destination_location)

            if converted_times:
                # Send the regular conversion response
                await message.channel.send("\n".join(converted_times))
            else:
                await message.channel.send(
                    "Timezone(s) unsupported - type 'tlist' for supported timezones and cities."
                )
        except ValueError:
            await message.channel.send(
                "Invalid syntax. Use `timec Xam/pm <origin location> to <destination location>` or `timec <time> @user1 to @user2`."
            )
    else:
        await message.channel.send(
            "Invalid syntax. Use `timec <time> <origin location> to <destination location>` or `timec <time> @user1 to @user2`."
        )

# actual conversion happens here (hopefully)
async def handle_conversion(message, full_response):
    try:
        parts = message.content.split()
        
        # Ensure correct number of elements
        if len(parts) < 5:
            await message.channel.send("Invalid syntax. Use `conv [amount] [from_currency] to [target_currency]`.")
            return

        amount = parts[1]
        from_currency = parts[2].upper()
        to_currency = parts[4].upper()

        # Validate currencies before processing
        if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
            supported_currencies = "\n".join(
                f"{i+1}. {CURRENCY_NAMES[c][1]} ({c})" for i, c in enumerate(SUPPORTED_CURRENCIES)
            )
            await message.channel.send(
                f"**Unsupported currency. Supported currencies are:**\n{supported_currencies}\n\n"
                "**To use the currency converter, type:**\n`conv [amount] [from_currency] to [target_currency]`\n"
                "`convf [amount] [from_currency] to [target_currency]` will return more information with source."
            )
            return

        # Convert amount to float
        amount = float(amount)
        
        rate, high_30, low_30, average_30, change_30, url = get_exchange_rate(from_currency, to_currency)

        if rate:
            converted_amount = amount * rate

            from_currency_singular, from_currency_plural = CURRENCY_NAMES[from_currency]
            to_currency_singular, to_currency_plural = CURRENCY_NAMES[to_currency]

            from_currency_name = from_currency_singular if amount == 1 else from_currency_plural
            to_currency_name = to_currency_singular if round(converted_amount, 2) == 1.00 else to_currency_plural

            if full_response:
                await message.channel.send(
                    f"**{amount} {from_currency_name}** is approximately **{converted_amount:.2f} {to_currency_name}** at an exchange rate of **{rate:.4f}**.\n"
                    f"In the past 30 days, the **high** was {high_30}, the **low** was {low_30}, with an **average** of {average_30} and a **change** of {change_30}.\n"
                    f"Click here for additional info: [source]({url})"
                )
            else:
                await message.channel.send(
                    f"**{amount} {from_currency_name}** is approximately **{converted_amount:.2f} {to_currency_name}** at an exchange rate of **{rate:.4f}**."
                )
        else:
            await send_error("Exchange rate or historical data not found.", message)
    except Exception as e:
        await send_error(f"Error: {str(e)}", message)

async def send_error(error_message, original_message):
    error_channel = client.get_channel(ERROR_CHANNEL_ID)
    if error_channel:
        await error_channel.send(f"Error in processing request from {original_message.author}: {error_message}")
    else:
        print("Error channel not found. Please set a valid ERROR_CHANNEL_ID.")

#async def send_periodic_message():
   # await client.wait_until_ready()  # Ensure bot is fully ready
   # channel = client.get_channel(PERIODIC_CHANNEL_ID)
   # while True:
     #   if channel:
     #       await channel.send("This is a periodic message sent every 28 minutes. Prevents dynos sleeping on heroku.")
     #   await asyncio.sleep(500 * 60)  # Wait 28 minutes


# @tree.command(name="active", description="Ping to keep the bot eligible")
# async def active_command(interaction: discord.Interaction):
#     await interaction.response.send_message("Good job, you've executed a useless command.")

#weather_command
@tree.command(name="weather", description="Get the current weather for a user or location")
@app_commands.describe(user_or_location="@user, city, country or abbreviation")
async def weather_command(interaction: discord.Interaction, user_or_location: str):
    await interaction.response.defer()

    # Determine if it's a user mention
    user_or_location = user_or_location.strip()
    if user_or_location.startswith("<@") and user_or_location.endswith(">"):
        user_id = user_or_location[2:-1].replace("!", "")  # Strip <@! >
        try:
            uid = str(int(user_id))
        except ValueError:
            await interaction.followup.send("Invalid user mention.")
            return

        if uid in USER_LOCATION_MAPPING:
            username, location = USER_LOCATION_MAPPING[uid]
        else:
            await interaction.followup.send("This user's location isn't in the database.")
            return
    else:
        location = user_or_location
        username = None

    try:
        async with aiohttp.ClientSession() as session:
            # Get coordinates for location
            geocoding_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={WEATHER_API_KEY}"
            async with session.get(geocoding_url) as response:
                if response.status != 200:
                    await interaction.followup.send("Sorry, I couldn't find that location.")
                    return
                
                geocode_data = await response.json()
                if not geocode_data:
                    await interaction.followup.send("Sorry, I couldn't find that location.")
                    return

                lat = geocode_data[0]['lat']
                lon = geocode_data[0]['lon']
                location_name = geocode_data[0]['name']
                country = geocode_data[0]['country']

            # Get weather data
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric"
            async with session.get(weather_url) as response:
                if response.status != 200:
                    await interaction.followup.send("Sorry, I couldn't fetch the weather data.")
                    return
                
                weather_data = await response.json()

        temperature = round(weather_data['main']['temp'])
        condition = weather_data['weather'][0]['description']
        temp_max = round(weather_data['main']['temp_max'])
        temp_min = round(weather_data['main']['temp_min'])

        if username:
            msg = (
                f"For **{username}**, it's **{condition}** and **{temperature} °C** in **{location_name}**, {country} today. "
                f"They can expect highs of {temp_max} °C and lows of {temp_min} °C."
            )
        else:
            msg = (
                f"It's **{condition}** and **{temperature} °C** in **{location_name}**, {country} today. "
                f"Expect highs of {temp_max} °C and lows of {temp_min} °C."
            )

        await interaction.followup.send(msg)

    except Exception as e:
        await interaction.followup.send(f"An error occurred while fetching weather data: {str(e)}")


#convert_command
@tree.command(name="convert", description="Convert between currencies")
@app_commands.describe(
    amount="Amount to convert",
    from_currency="Currency to convert from (e.g. USD)",
    to_currency="Currency to convert to (e.g. EUR)"
)
async def convert_command(interaction: discord.Interaction, amount: float, from_currency: str, to_currency: str):
    await interaction.response.defer()
    
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency not in SUPPORTED_CURRENCIES or to_currency not in SUPPORTED_CURRENCIES:
        await interaction.followup.send("Unsupported currency. Use `/clist` for supported codes.")
        return

    rate, *_ = get_exchange_rate(from_currency, to_currency)

    if rate:
        converted = amount * rate
        from_name = CURRENCY_NAMES[from_currency][1 if amount != 1 else 0]
        to_name = CURRENCY_NAMES[to_currency][1 if converted != 1 else 0]

        await interaction.followup.send(
            f"**{amount} {from_name}** ≈ **{converted:.2f} {to_name}** (rate: {rate:.4f})"
        )
    else:
        await interaction.followup.send("Exchange rate lookup failed.")


#help_command
@tree.command(name="help", description="Show README / help pages")
async def whelp_command(interaction: discord.Interaction):
    current_page = 0
    total_pages = len(sections)
    embed = build_embed(sections[current_page])
    view = HelpView(current_page, total_pages)
    await interaction.response.send_message(embed=embed, view=view)

#translate_command
@tree.command(name="translate", description="Translate text to English")
@app_commands.describe(text="The text you want translated")
async def translate_command(interaction: discord.Interaction, text: str):
    try:
        url = f"https://translate.google.com/m?sl=auto&tl=en&q={text}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            result = soup.find('div', {'class': 'result-container'})

            if result:
                await interaction.response.send_message(f"**Translation:**\n{result.text}")
            else:
                await interaction.response.send_message("Sorry, I couldn't translate that text.")
        else:
            await interaction.response.send_message("Error accessing translation service.")
    except Exception as e:
        await interaction.response.send_message(f"Translation error: {e}")

#mlist_command
@tree.command(name="mlist", description="List server members and join dates")
async def mlist_command(interaction: discord.Interaction):
    guild = interaction.guild
    member_list = []

    async for member in guild.fetch_members():
        nickname = member.nick if member.nick else member.name
        join_date = member.joined_at.strftime('%b %d, %Y') if member.joined_at else 'N/A'
        member_list.append((nickname, join_date, member.joined_at))

    member_list.sort(key=lambda x: x[2])
    formatted = "\n".join(f"{i+1}. {n} [{d}]" for i, (n, d, _) in enumerate(member_list))

    embed = discord.Embed(
        title="Members in this server",
        description="Member | When they joined the server\n" + formatted,
        color=discord.Color.dark_red()
    )

    await interaction.response.send_message(embed=embed)

#jdlist_command
@tree.command(name="jdlist", description="List account creation dates of members")
async def jdlist_command(interaction: discord.Interaction):
    guild = interaction.guild
    account_list = []

    async for member in guild.fetch_members():
        nickname = member.nick if member.nick else member.name
        creation_date = member.created_at.strftime('%b %d, %Y') if member.created_at else 'N/A'
        account_list.append((nickname, creation_date, member.created_at))

    account_list.sort(key=lambda x: x[2])
    formatted = "\n".join(f"{i + 1}. {n} [{d}]" for i, (n, d, _) in enumerate(account_list))

    embed = discord.Embed(
        title="Members' Account Creation Dates",
        description=formatted,
        color=discord.Color.dark_red()
    )

    await interaction.response.send_message(embed=embed)

#serverinfo_command
@tree.command(name="serverinfo", description="Display info about this server")
async def server_info_command(interaction: discord.Interaction):
    guild = interaction.guild
    if guild:
        embed = discord.Embed(title=f"Server Info for **{guild.name}**", color=discord.Color.blue())
        embed.add_field(name="Server ID", value=guild.id, inline=False)
        embed.add_field(name="Owner", value="Who knows?", inline=False)
        embed.add_field(name="Member Count", value=guild.member_count, inline=False)
        embed.add_field(name="Boost Count", value=guild.premium_subscription_count, inline=False)
        embed.add_field(name="Text Channels", value=len(guild.text_channels), inline=False)
        embed.add_field(name="Voice Channels", value=len(guild.voice_channels), inline=False)
        embed.add_field(name="Created At", value=guild.created_at.strftime('%Y-%m-%d %H:%M:%S'), inline=False)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("This command must be used in a server.")

from discord.app_commands import Parameter

from discord.app_commands import Parameter

#time_command
@tree.command(name="time", description="Get current time for a user or by location")
@app_commands.describe(user_or_location="@user or a city/country/abbreviation")
async def time_command(interaction: discord.Interaction, user_or_location: str):
    location = user_or_location.strip()
    
    # Check if it's a user mention
    if location.startswith("<@") and location.endswith(">"):
        user_id = location[2:-1].replace("!", "")  # remove optional "!" for nicknames
        try:
            user_id_int = int(user_id)
        except ValueError:
            await interaction.response.send_message("Invalid user mention.")
            return

        user_data = USER_TIMEZONE_MAPPING.get(user_id_int)
        if not user_data:
            await interaction.response.send_message("No timezone information found for that user.")
            return

        username, abbr = user_data
        for country, cities in timezones_dict.items():
            for city, abbreviation, tz_name, gmt_offset in cities:
                if abbreviation.lower() == abbr.lower():
                    tz = pytz.timezone(tz_name)
                    city_time = datetime.now(tz).strftime('%I:%M %p')
                    await interaction.response.send_message(
                        f"It's **{city_time}** for **{username}**, in {city.title()}, {country.title()}, {gmt_offset}."
                    )
                    return
        await interaction.response.send_message(f"City abbreviation `{abbr}` not found.")
    else:
        # Fallback to standard location input
        times = get_current_time(location)
        if times:
            formatted = [t.replace(location.upper(), location.title()) for t in times]
            await interaction.response.send_message("\n".join(formatted))
        else:
            await interaction.response.send_message("Timezone(s) unsupported — use `/tlist` for supported timezones and cities.")



#timeconvert_command
@tree.command(name="timeconvert", description="Convert time between two users or locations")
@app_commands.describe(
    time_str="Time to convert (e.g. 5pm, 17:00)",
    from_user="@User or city/abbreviation",
    to_user="@User or city/abbreviation"
)
async def timeconvert_command(interaction: discord.Interaction, time_str: str, from_user: str, to_user: str):
    from_input = from_user.strip()
    to_input = to_user.strip()

    def extract_user_id(mention: str):
        if mention.startswith("<@") and mention.endswith(">"):
            return int(mention[2:-1].replace("!", ""))
        return None

    from_user_id = extract_user_id(from_input)
    to_user_id = extract_user_id(to_input)

    if from_user_id and to_user_id:
        from_data = USER_TIMEZONE_MAPPING.get(from_user_id)
        to_data = USER_TIMEZONE_MAPPING.get(to_user_id)

        if not from_data or not to_data:
            await interaction.response.send_message("One or both users do not have timezone info saved.")
            return

        from_name, from_abbr = from_data
        to_name, to_abbr = to_data

        results = convert_time(time_str, from_abbr, to_abbr)
        if results:
            # Clean formatting: get the converted time only (right side of `is`)
            clean_time = results[0].split(" is ")[1]
            response = f"{time_str} for **{from_name}** in {from_abbr.upper()} is {clean_time} for **{to_name}**."
            await interaction.response.send_message(response)
        else:
            await interaction.response.send_message("Couldn't convert between user timezones.")
        return

    # Fallback: use as city or abbreviation
    results = convert_time(time_str, from_input, to_input)
    if results:
        await interaction.response.send_message("\n".join(results))
    else:
        await interaction.response.send_message(
            "Unsupported location or timezone. Try `/tlist` for valid entries."
        )



@tree.command(name="clist", description="List all supported currencies")
async def clist_command(interaction: discord.Interaction):
    embed = get_currency_list_embed(SUPPORTED_CURRENCIES, CURRENCY_NAMES)
    await interaction.response.send_message(embed=embed)

@tree.command(name="tlist", description="List supported timezones and abbreviations")
async def tlist_command(interaction: discord.Interaction):
    embed = get_timezone_list_embed(timezones_dict, COUNTRY_ABBREVIATIONS)
    await interaction.response.send_message(embed=embed)

@tree.command(name="ping", description="Check bot latency")
async def ping_command(interaction: discord.Interaction):
    latency = round(client.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency: `{latency}ms`")

@tree.command(name="remind", description="Set a reminder")
@app_commands.describe(duration="e.g. 10m, 1h, 30s", message="Reminder message")
async def remind_command(interaction: discord.Interaction, duration: str, message: str):
    unit = duration[-1]
    num = duration[:-1]
    
    if not num.isdigit() or unit not in ("s", "m", "h"):
        await interaction.response.send_message("Invalid time format. Use something like `10s`, `5m`, or `2h`.")
        return

    seconds = int(num) * {"s": 1, "m": 60, "h": 3600}[unit]
    await interaction.response.send_message(f"Got it! I'll remind you in {duration} ⏰.")

    await asyncio.sleep(seconds)
    await interaction.followup.send(f"🔔 **Reminder**: {message}")

@tree.command(name="convertunit", description="Convert between basic units")
@app_commands.describe(value="Value to convert", from_unit="Unit to convert from (km<->mi, kg<->lb, or c<->f)", to_unit="Unit to convert to (km<->mi, kg<->lb, or c<->f)")
async def convertunit_command(interaction: discord.Interaction, value: float, from_unit: str, to_unit: str):
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()
    conversions = {
        ("km", "mi"): lambda v: v * 0.621371,
        ("mi", "km"): lambda v: v / 0.621371,
        ("kg", "lb"): lambda v: v * 2.20462,
        ("lb", "kg"): lambda v: v / 2.20462,
        ("c", "f"): lambda v: (v * 9/5) + 32,
        ("f", "c"): lambda v: (v - 32) * 5/9,
    }

    key = (from_unit, to_unit)
    if key not in conversions:
        await interaction.response.send_message("Unsupported conversion. Try km<->mi, kg<->lb, or c<->f.")
        return

    result = conversions[key](value)
    await interaction.response.send_message(f"{value} {from_unit} ≈ {result:.2f} {to_unit}")


@tree.command(name="whois", description="Get info about a user")
@app_commands.describe(user="The user to look up")
async def whois_command(interaction: discord.Interaction, user: discord.Member):
    user = await interaction.guild.fetch_member(user.id)
    uid = str(user.id)  # For string-based lookups (location and description)
    uid_int = user.id   # For integer-based lookups (timezone)

    descriptions = load_descriptions()
    desc = descriptions.get(uid)

    embed = discord.Embed(
        title=f"Profile: {user.display_name}",
        color=user.top_role.colour if user.top_role.colour.value else discord.Color.dark_gray()
    )
    embed.set_thumbnail(url=user.display_avatar.url)

    embed.add_field(name="Account Created", value=user.created_at.strftime('%b %d, %Y'), inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime('%b %d, %Y'), inline=True)

    # Roles
    roles = [r.mention for r in user.roles if r != interaction.guild.default_role]
    if roles:
        embed.add_field(name="Roles", value=", ".join(roles), inline=False)

    # Timezone check - use integer ID
    if uid_int in USER_TIMEZONE_MAPPING:
        username, abbr = USER_TIMEZONE_MAPPING[uid_int]
        timezone_found = False
        for country_cities in timezones_dict.values():
            if timezone_found:
                break
            for city, short, tz, offset in country_cities:
                if short.lower() == abbr.lower():
                    embed.add_field(name="Timezone", value=f"{tz} ({offset})", inline=False)
                    timezone_found = True
                    break

    # Location check - use string ID
    if uid in USER_LOCATION_MAPPING:
        username, location = USER_LOCATION_MAPPING[uid]
        embed.add_field(name="Location", value=location, inline=False)

    # Description
    if desc:
        embed.add_field(name="Description", value=desc, inline=False)

    await interaction.response.send_message(embed=embed)


@tree.command(name="desc", description="Set your public description for /whois")
@app_commands.describe(description="Your set description will show up with the /whois command")
async def setdesc_command(interaction: discord.Interaction, description: str):
    uid = str(interaction.user.id)
    data = load_descriptions()
    data[uid] = description
    save_descriptions(data)

    await interaction.response.send_message("Your description has been saved.")


client.run(DISCORD_TOKEN)
