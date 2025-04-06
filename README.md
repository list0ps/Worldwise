# Worldwise Discord Bot

This bot was designed to be used in my personal discord server with an exceedingly international group of friends. It's built entirely using python and the discord.py library, with a tinge of web scraping and API integration (also some json architecture).

Though most of the bot's functionality is easily attainable through a quick google search, it served the purpose of my hyperfixiative means of stress relief over a week long project. 

*still being updated.

## Commands Overview

### Functional Commands

## Time & Timezones

| Command            | Description                                                                   | Example Usage                                 |
|--------------------|-------------------------------------------------------------------------------|-----------------------------------------------|
| `/time`            | Get the current time in a city, timezone abbreviation or <@mentionuser>                      | `/time Tokyo, /time <@user>`                                 |
| `/timeconvert`     | Convert a time from one location to another.                                  | `/timeconvert 7:30am London to Sydney`        |
| `/tlist`           | Lists all supported timezones and abbreviations.                              | `/tlist`                                      |

---

## Weather

| Command        | Description                                                       | Example Usage                  |
|----------------|-------------------------------------------------------------------|--------------------------------|
| `/weather`     | Get current weather for a location.                               | `/weather Paris, FR`           |

---

## Currency & Units

| Command            | Description                                                                 | Example Usage                              |
|--------------------|-----------------------------------------------------------------------------|---------------------------------------------|
| `/convert`         | Convert an amount between two currencies.                                   | `/convert 100 USD to EUR`                   |
| `/clist`           | Lists supported currency codes and names.                                   | `/clist`                                    |
| `/convertunit`     | Convert between basic units (km↔mi, kg↔lb, °C↔°F).                          | `/convertunit 10 km to mi`                  |

---

## Utility & Reminders

| Command        | Description                                                        | Example Usage                      |
|----------------|--------------------------------------------------------------------|------------------------------------|
| `/remind`      | Set a timed reminder. Supports `s`, `m`, and `h` for time units.   | `/remind 15m Take out the bin!`    |
| `/translate`   | Translates provided text into English.                             | `/translate bonjour`               |
| `/uptime`      | Show how long the bot has been running.                            | `/uptime`                          |
| `/ping`        | Check the bot's current latency.                                   | `/ping`                            |
| `/active`      | Ping the bot to keep it awake (used for uptime hacks).             | `/active`                          |
| `/whelp`       | View multi-page interactive help embed.                            | `/whelp`                           |

---

## Server Info & Members

| Command        | Description                                                       | Example Usage                      |
|----------------|-------------------------------------------------------------------|------------------------------------|
| `/serverinfo`  | Shows general info about the current server.                      | `/serverinfo`                      |
| `/mlist`       | Lists all members and when they joined.                           | `/mlist`                           |
| `/jdlist`      | Lists members and their account creation dates.                   | `/jdlist`                          |
| `/whois`       | Shows user info (join date, timezone, description, etc.).         | `/whois @User`                     |

---

## User Descriptions

| Command        | Description                                                       | Example Usage                            |
|----------------|-------------------------------------------------------------------|------------------------------------------|
| `/desc`        | Set your own description for display in `/whois`.                 | `/desc Genomics student in Melbourne`    |
| `/descadmin`   | *(Admin-only)* Set or clear someone else's description.           | `/descadmin @User clear`                 |
| `/desclist`    | *(Admin-only)* View all saved descriptions.                       | `/desclist`                              |

---

## Admin-Only Commands

| Command        | Description                                                              | Example Usage                             |
|----------------|--------------------------------------------------------------------------|-------------------------------------------|
| `/guilds`      | Lists all servers the bot is currently in.                               | `/guilds`                                  |
| `/shutdown`    | Safely shuts the bot down.                                               | `/shutdown`                                |
| `/clear`       | Deletes a number of recent messages in the channel.                      | `/clear 20`                                 |
| `/announce`    | Sends a message as the bot in a specific channel.                        | `/announce #general Meeting in 5 mins!`    |
| `/rolelist`    | Lists all roles in the server and the members in each.                   | `/rolelist`                                |

---