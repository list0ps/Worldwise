# Time & Currency Conversion Discord Bot

This is a Discord bot designed to provide time look-ups and time and currency conversions. Made for my discord server with an exceedingly international group of friends.

## Features
- **Time Zone Conversion:** Convert time from one location to another, including support for multiple time zones within a country.
- **Time Lookup:** Simply gives you the time of a supported location you ask for.
- **Currency Conversion:** Convert amounts between various currencies and get additional information like historical data and exchange rates.
- **Periodic Messages:** Prevent Heroku dynos from going to sleep by sending periodic messages.
- **User-Friendly Commands:** easy-to-use commands for conversion and time retrieval.



## Command List
**All commands are case in-sensitive.**
| Command                                                              | Description                                                                 | Example                                      |
|----------------------------------------------------------------------|-----------------------------------------------------------------------------|----------------------------------------------|
| `time <location>`                                                     | Returns the current time for the specified city. If a country is used in `location`, returns cities in that country. | `time Kuala Lumpur`, `time MY`, `time Malaysia` |
| `convt <time> <origin location> to <destination location>`             | Converts time from one location to another. Returns cities in countries if country is mentioned. | `convt 6pm KL to Australia`, `convt 9am NYC to London` |
| `conv <amount> <from_currency> to <target_currency>`                   | Converts a given amount from one currency to another. | `conv 100 USD to CAD`, `conv 100 EUR to GBP` |
| `convf <amount> <from_currency> to <target_currency>`                  | Returns conversion + additional info (high, low, average, change). | `convf 100 USD to CAD`, `convf 100 EUR to GBP` |
| `chelp`                                                              | Provides instructions and syntax  on currency-related commands.                                      | `chelp`                                    |
| `clist`                                                               | Lists all supported currencies and short codes like "USD".                              | `clist`                                     |
| `cthelp`                                                              | Provides time-related syntax and instructions.         | `ctlist`                                    |
| `ctlist`                                                              | Lists all supported cities and countries for time-related commands.         | `ctlist`        

## How the Bot Works

This bot provides several utilities, including currency conversion and time zone conversion, all through Discord messages. 

- The bot is built using the `discord.py` library, which allows it to interact with Discord's API.
- Time zone information is stored in a dictionary (`timezones_dict`) that maps countries/cities to their respective time zones, supporting case-insensitive lookups for location names.
- Currency data is fetched through a web scrapping method, ensuring that the latest exchange rates are always available. The bot supports a wide range of currencies, and detailed exchange rate information (high, low, average, etc.) is retrieved from historical data.
- The bot also includes error handling to ensure smooth user interactions and provides feedback if an unsupported currency or time zone is used.

## Functions in the Code

The bot's functionality is divided into several core functions.

### 1. `convert_time(time_str, from_location, to_location)`
This function is responsible for converting a given time from one time zone to another. It accepts three parameters:
- `time_str`: The time to convert, given in a 12-hour format (e.g., "6pm").
- `from_location`: The origin location (city or country) of the time.
- `to_location`: The target location to convert the time to.

The function uses a dictionary (`timezones_dict`) to look up the time zone for both the origin and destination. It then converts the input time to the correct time zone and returns the result, formatted in a human-readable manner. If multiple time zones exist for a location, the function handles those as well.

### 2. `handle_conversion(message, full_response)`
This function handles the `conv` and `convf` commands for currency conversion. It is invoked when a user requests a conversion using either `conv` for a quick response or `convf` for a full response. It works as follows:
- The function splits the message to extract the amount, source currency, and target currency.
- It validates the input currencies against a predefined list (`SUPPORTED_CURRENCIES`).
- If valid, it retrieves the exchange rate and performs the conversion. The `full_response` flag determines whether additional details (e.g., high/low/average data for the last 30 days) are included in the response.
- If the input is invalid or the currency data cannot be found, it sends an error message to the user.

### 3. `get_exchange_rate(from_currency, to_currency)`
This function retrieves the current exchange rate between two currencies. It uses a web-scrapping method (maps to HTML div classes) to fetch the exchange rate and related historical data (such as 30-day high, low, average, and percentage change). This data is then returned to the `handle_conversion` function for further processing and display.

### 4. `send_error(error_message, original_message)`
Error logs. 

### 5. `send_periodic_message()`
This function is a background task that periodically sends a message to a specific channel. It runs every 28 minutes, preventing the Heroku dyno from going to sleep. This ensures the bot remains active and responsive.

### 6. `on_ready()`
This is a built-in Discord event handler that is triggered when the bot successfully logs in and is ready to start responding to commands. In this function:
- The bot sends a startup message to a designated channel, notifying users that the bot is now online and functional.
- It also starts the periodic message task to keep the bot alive on platforms like Heroku.

### 7. `on_message(message)`
This is another built-in event handler that listens for messages sent in channels where the bot has access. Based on the message content, it determines which command to process. The main responsibilities of this function are:
- Responding to `conv` and `convf` commands by invoking the `handle_conversion` function.
- Responding to `time` and `convt` commands by invoking the `convert_time` function for time zone conversions.
- Providing help messages for users with the `chelp` and `cthelp` commands, explaining how to use the bot.
- Displaying a list of supported currencies and time zones when the user types `clist` or `ctlist`.

These functions work together to create a seamless user experience by converting currencies, times, and providing additional information on request.


