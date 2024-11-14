import discord
import requests
from bs4 import BeautifulSoup
import re
import os
import asyncio  # Import asyncio for background tasks
import pytz  # Add this for timezone handling
from datetime import datetime  # Add this for date and time handling

# Supported currencies
SUPPORTED_CURRENCIES = ['USD', 'NZD', 'CAD', 'BDT', 'MYR', 'MUR', 'EUR', 'EGP', 'SAR', 'TRY', 'GBP', 'AUD']

# Globally defining the timezones dictionary
timezones_dict = {
    'newzealand': [('auckland', 'akl', 'Pacific/Auckland', 'GMT+13'), 
                   ('wellington', 'wlg', 'Pacific/Auckland', 'GMT+13'), 
                   ('christchurch', 'chc', 'Pacific/Auckland', 'GMT+13'), 
                   ('hamilton', 'hlz', 'Pacific/Auckland', 'GMT+13')],
    'australia': [('sydney', 'syd', 'Australia/Sydney', 'GMT+11'), 
                  ('melbourne', 'mel', 'Australia/Melbourne', 'GMT+11'), 
                  ('brisbane', 'bne', 'Australia/Brisbane', 'GMT+10'), 
                  ('perth', 'per', 'Australia/Perth', 'GMT+8'), 
                  ('adelaide', 'adl', 'Australia/Adelaide', 'GMT+10.5'), 
                  ('canberra', 'cbr', 'Australia/Sydney', 'GMT+11')],
    'bangladesh': [('dhaka', 'dac', 'Asia/Dhaka', 'GMT+6')],
    'malaysia': [('kuala lumpur', 'kl', 'Asia/Kuala_Lumpur', 'GMT+8')],
    'mauritius': [('port louis', 'plu', 'Indian/Mauritius', 'GMT+4')],
    'canada': [('toronto', 'yyz', 'America/Toronto', 'GMT-5'), 
               ('vancouver', 'yvr', 'America/Vancouver', 'GMT-8'), 
               ('montreal', 'yul', 'America/Toronto', 'GMT-5'), 
               ('calgary', 'yyc', 'America/Edmonton', 'GMT-7'), 
               ('ottawa', 'yow', 'America/Toronto', 'GMT-5')],
    'unitedstates': [('new york', 'nyc', 'America/New_York', 'GMT-5'), 
                     ('los angeles', 'lax', 'America/Los_Angeles', 'GMT-8'), 
                     ('chicago', 'chi', 'America/Chicago', 'GMT-6'), 
                     ('houston', 'hou', 'America/Chicago', 'GMT-6'), 
                     ('phoenix', 'phx', 'America/Phoenix', 'GMT-7'), 
                     ('seattle', 'sea', 'America/Los_Angeles', 'GMT-8'), 
                     ('miami', 'mia', 'America/New_York', 'GMT-5')],
    'england': [('london', 'lon', 'Europe/London', 'GMT+0'), 
                ('manchester', 'man', 'Europe/London', 'GMT+0'), 
                ('birmingham', 'bhx', 'Europe/London', 'GMT+0')],
    'germany': [('berlin', 'ber', 'Europe/Berlin', 'GMT+1'), 
                ('munich', 'muc', 'Europe/Berlin', 'GMT+1'), 
                ('frankfurt', 'fra', 'Europe/Berlin', 'GMT+1')],
    'france': [('paris', 'par', 'Europe/Paris', 'GMT+1'), 
               ('lyon', 'lys', 'Europe/Paris', 'GMT+1'), 
               ('marseille', 'mrs', 'Europe/Paris', 'GMT+1')],
    'italy': [('rome', 'rom', 'Europe/Rome', 'GMT+1'), 
              ('milan', 'mil', 'Europe/Rome', 'GMT+1'), 
              ('naples', 'nap', 'Europe/Rome', 'GMT+1')],
    'denmark': [('copenhagen', 'cph', 'Europe/Copenhagen', 'GMT+1')],
    'netherlands': [('amsterdam', 'ams', 'Europe/Amsterdam', 'GMT+1'), 
                    ('rotterdam', 'rtm', 'Europe/Amsterdam', 'GMT+1')],
    'finland': [('helsinki', 'hel', 'Europe/Helsinki', 'GMT+2')],
    'switzerland': [('zurich', 'zrh', 'Europe/Zurich', 'GMT+1'), 
                    ('geneva', 'gva', 'Europe/Zurich', 'GMT+1')],
    'luxembourg': [('luxembourg', 'lxm', 'Europe/Luxembourg', 'GMT+1')],
    
}

# dictionary to store user ID, username, and city mappings
USER_TIMEZONE_MAPPING = {
    340485392434200576: ("list", "hlz"),
    744440440786255994: ("Bronoy", "dac"),
    697901157472796826: ("Bush", "dac"),
    439530718352375827: ("curlysandwich", "nyc"),
    626150404333371422: ("gl1vch", "yyz"),
    313373154812755969: ("Ibrahim", "kl"),
    701305433633194018: ("ItznotHawk", "mel"),
    709061499066515476: ("mehnaz", "nyc"),
    719836306569429064: ("Moose", "dac"),
    665657749207777351: ("Nay", "yyz"),
    428113253726683137: ("Nowfel", "yyz"),
    544753860858871831: ("ORANGMAN", "akl"),
    392683322805059587: ("Relic", "dac"),
    422394995266551808: ("Shamo_99", "lxm"),
    692430092592218123: ("Skibby", "kl"),
    368379417208029185: ("strangyyy", "dac"),
    488021414759366668: ("tooshiewooshie", "dac"),
    426522676581105676: ("Verse", "dac"),
    487064547832627200: ("Alex", "plu"),
    960839376563236894: ("Yashfi", "kl"),
    219797015066968064: ("Zer0", "yyz"),
    425981881138413568: ("ZiWei", "kl"),
}

# Mapping currency codes to (singular name, plural name) where anything but 1 returns plural (or so i hope)
CURRENCY_NAMES = {
    'USD': ('United States Dollar', 'United States Dollars'),
    'NZD': ('New Zealand Dollar', 'New Zealand Dollars'),
    'CAD': ('Canadian Dollar', 'Canadian Dollars'),
    'BDT': ('Bangladeshi Taka', 'Bangladeshi Taka'),
    'MYR': ('Malaysian Ringgit', 'Malaysian Ringgit'),
    'MUR': ('Mauritian Rupee', 'Mauritian Rupees'),
    'EUR': ('Euro', 'Euros'),
    'EGP': ('Egyptian Pound', 'Egyptian Pounds'),
    'SAR': ('Saudi Riyal', 'Saudi Riyals'),
    'TRY': ('Turkish Lira', 'Turkish Lira'),
    'GBP': ('British Pound', 'British Pounds'),
    'AUD': ('Australian Dollar', 'Australian Dollars')
}

# Abbreviation mapping for countries used 'ctlist' in on_message
COUNTRY_ABBREVIATIONS = {
    'newzealand': 'NZ',
    'australia': 'AU',
    'bangladesh': 'BD',
    'malaysia': 'MY',
    'mauritius': 'MU',
    'canada': 'CA',
    'unitedstates': 'US',
    'england': 'UK',
    'germany': 'GER',
    'france': 'FR',
    'italy': 'IT',
    'denmark': 'DK',
    'netherlands': 'NL',
    'finland': 'FI',
    'switzerland': 'CH',
    'luxembourg' : 'LU'
}

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
    
    
# Updated `get_current_time` function with additional cities for mor countries
def get_current_time(location):
    # Dictionary of countries, abbreviations, cities and GMT offsets
    timezones_dict = {
        'newzealand': [('auckland', 'akl', 'Pacific/Auckland', 'GMT+13'), 
                       ('wellington', 'wlg', 'Pacific/Auckland', 'GMT+13'), 
                       ('christchurch', 'chc', 'Pacific/Auckland', 'GMT+13'), 
                       ('hamilton', 'hlz', 'Pacific/Auckland', 'GMT+13')],
        'nz': [('auckland', 'akl', 'Pacific/Auckland', 'GMT+13'), 
               ('wellington', 'wlg', 'Pacific/Auckland', 'GMT+13'), 
               ('christchurch', 'chc', 'Pacific/Auckland', 'GMT+13'), 
               ('hamilton', 'hlz', 'Pacific/Auckland', 'GMT+13')],
        'australia': [('sydney', 'syd', 'Australia/Sydney', 'GMT+11'), 
                      ('melbourne', 'mel', 'Australia/Melbourne', 'GMT+11'), 
                      ('brisbane', 'bne', 'Australia/Brisbane', 'GMT+10'), 
                      ('perth', 'per', 'Australia/Perth', 'GMT+8'), 
                      ('adelaide', 'adl', 'Australia/Adelaide', 'GMT+10.5'), 
                      ('canberra', 'cbr', 'Australia/Sydney', 'GMT+11')],
        'au': [('sydney', 'syd', 'Australia/Sydney', 'GMT+11'), 
               ('melbourne', 'mel', 'Australia/Melbourne', 'GMT+11'), 
               ('brisbane', 'bne', 'Australia/Brisbane', 'GMT+10'), 
               ('perth', 'per', 'Australia/Perth', 'GMT+8'), 
               ('adelaide', 'adl', 'Australia/Adelaide', 'GMT+10.5'), 
               ('canberra', 'cbr', 'Australia/Sydney', 'GMT+11')],
        'bangladesh': [('dhaka', 'dac', 'Asia/Dhaka', 'GMT+6')],
        'bd': [('dhaka', 'dac', 'Asia/Dhaka', 'GMT+6')],
        'malaysia': [('kuala lumpur', 'kl', 'Asia/Kuala_Lumpur', 'GMT+8')],
        'my': [('kuala lumpur', 'kl', 'Asia/Kuala_Lumpur', 'GMT+8')],
        'mauritius': [('port louis', 'plu', 'Indian/Mauritius', 'GMT+4')],
        'mu': [('port louis', 'plu', 'Indian/Mauritius', 'GMT+4')],
        'canada': [('toronto', 'yyz', 'America/Toronto', 'GMT-5'), 
                   ('vancouver', 'yvr', 'America/Vancouver', 'GMT-8'), 
                   ('montreal', 'yul', 'America/Toronto', 'GMT-5'), 
                   ('calgary', 'yyc', 'America/Edmonton', 'GMT-7'), 
                   ('ottawa', 'yow', 'America/Toronto', 'GMT-5')],
        'ca': [('toronto', 'yyz', 'America/Toronto', 'GMT-5'), 
               ('vancouver', 'yvr', 'America/Vancouver', 'GMT-8'), 
               ('montreal', 'yul', 'America/Toronto', 'GMT-5'), 
               ('calgary', 'yyc', 'America/Edmonton', 'GMT-7'), 
               ('ottawa', 'yow', 'America/Toronto', 'GMT-5')],
        'unitedstates': [('new york', 'nyc', 'America/New_York', 'GMT-5'), 
                         ('los angeles', 'lax', 'America/Los_Angeles', 'GMT-8'),
                         ('chicago', 'chi', 'America/Chicago', 'GMT-6'),
                         ('houston', 'hou', 'America/Chicago', 'GMT-6'),
                         ('phoenix', 'phx', 'America/Phoenix', 'GMT-7'),
                         ('seattle', 'sea', 'America/Los_Angeles', 'GMT-8'),
                         ('miami', 'mia', 'America/New_York', 'GMT-5'),
                         ('atlanta', 'atl', 'America/New_York', 'GMT-5'),
                         ('dallas', 'dfw', 'America/Chicago', 'GMT-6')],
        'us': [('new york', 'nyc', 'America/New_York', 'GMT-5'), 
               ('los angeles', 'lax', 'America/Los_Angeles', 'GMT-8'),
               ('chicago', 'chi', 'America/Chicago', 'GMT-6'),
               ('houston', 'hou', 'America/Chicago', 'GMT-6'),
               ('phoenix', 'phx', 'America/Phoenix', 'GMT-7'),
               ('seattle', 'sea', 'America/Los_Angeles', 'GMT-8'),
               ('miami', 'mia', 'America/New_York', 'GMT-5'),
               ('atlanta', 'atl', 'America/New_York', 'GMT-5'),
               ('dallas', 'dfw', 'America/Chicago', 'GMT-6')],
        'england': [('london', 'lon', 'Europe/London', 'GMT+0'), 
                    ('manchester', 'man', 'Europe/London', 'GMT+0'), 
                    ('birmingham', 'bhx', 'Europe/London', 'GMT+0'), 
                    ('liverpool', 'lpl', 'Europe/London', 'GMT+0')],
        'uk': [('london', 'lon', 'Europe/London', 'GMT+0'), 
               ('manchester', 'man', 'Europe/London', 'GMT+0'), 
               ('birmingham', 'bhx', 'Europe/London', 'GMT+0'), 
               ('liverpool', 'lpl', 'Europe/London', 'GMT+0')],
        'germany': [('berlin', 'ber', 'Europe/Berlin', 'GMT+1'), 
                    ('munich', 'muc', 'Europe/Berlin', 'GMT+1'), 
                    ('frankfurt', 'fra', 'Europe/Berlin', 'GMT+1')],
        'ger': [('berlin', 'ber', 'Europe/Berlin', 'GMT+1'), 
                    ('munich', 'muc', 'Europe/Berlin', 'GMT+1'), 
                    ('frankfurt', 'fra', 'Europe/Berlin', 'GMT+1')],
        'france': [('paris', 'par', 'Europe/Paris', 'GMT+1'), 
                   ('lyon', 'lys', 'Europe/Paris', 'GMT+1'), 
                   ('marseille', 'mrs', 'Europe/Paris', 'GMT+1')],
        'fr': [('paris', 'par', 'Europe/Paris', 'GMT+1'), 
                   ('lyon', 'lys', 'Europe/Paris', 'GMT+1'), 
                   ('marseille', 'mrs', 'Europe/Paris', 'GMT+1')],
        'italy': [('rome', 'rom', 'Europe/Rome', 'GMT+1'), 
                  ('milan', 'mil', 'Europe/Rome', 'GMT+1'), 
                  ('naples', 'nap', 'Europe/Rome', 'GMT+1')],
        'it': [('rome', 'rom', 'Europe/Rome', 'GMT+1'), 
                  ('milan', 'mil', 'Europe/Rome', 'GMT+1'), 
                  ('naples', 'nap', 'Europe/Rome', 'GMT+1')],
        'denmark': [('copenhagen', 'cph', 'Europe/Copenhagen', 'GMT+1')],
        'dk': [('copenhagen', 'cph', 'Europe/Copenhagen', 'GMT+1')],
        'netherlands': [('amsterdam', 'ams', 'Europe/Amsterdam', 'GMT+1'), 
                        ('rotterdam', 'rtm', 'Europe/Amsterdam', 'GMT+1')],
        'nl': [('amsterdam', 'ams', 'Europe/Amsterdam', 'GMT+1'), 
                        ('rotterdam', 'rtm', 'Europe/Amsterdam', 'GMT+1')],
        'finland': [('helsinki', 'hel', 'Europe/Helsinki', 'GMT+2')],
        'fi': [('helsinki', 'hel', 'Europe/Helsinki', 'GMT+2')],
        'switzerland': [('zurich', 'zrh', 'Europe/Zurich', 'GMT+1'), 
                        ('geneva', 'gva', 'Europe/Zurich', 'GMT+1')],
        'ch': [('zurich', 'zrh', 'Europe/Zurich', 'GMT+1'), 
                        ('geneva', 'gva', 'Europe/Zurich', 'GMT+1')],
        'luxembourg': [('luxembourg', 'lxm', 'Europe/Luxembourg', 'GMT+1')],
        'lu': [('luxembourg', 'lxm', 'Europe/Luxembourg', 'GMT+1')],

    }

    # Normalizing input for case-insensitive matching because alex is weird
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
    timezones_dict = {
        'newzealand': [('auckland', 'akl', 'Pacific/Auckland', 'GMT+13'), 
                       ('wellington', 'wlg', 'Pacific/Auckland', 'GMT+13'), 
                       ('christchurch', 'chc', 'Pacific/Auckland', 'GMT+13'), 
                       ('hamilton', 'hlz', 'Pacific/Auckland', 'GMT+13')],
        'nz': [('auckland', 'akl', 'Pacific/Auckland', 'GMT+13'), 
               ('wellington', 'wlg', 'Pacific/Auckland', 'GMT+13'), 
               ('christchurch', 'chc', 'Pacific/Auckland', 'GMT+13'), 
               ('hamilton', 'hlz', 'Pacific/Auckland', 'GMT+13')],
        'australia': [('sydney', 'syd', 'Australia/Sydney', 'GMT+11'), 
                      ('melbourne', 'mel', 'Australia/Melbourne', 'GMT+11'), 
                      ('brisbane', 'bne', 'Australia/Brisbane', 'GMT+10'), 
                      ('perth', 'per', 'Australia/Perth', 'GMT+8'), 
                      ('adelaide', 'adl', 'Australia/Adelaide', 'GMT+10.5'), 
                      ('canberra', 'cbr', 'Australia/Sydney', 'GMT+11')],
        'au': [('sydney', 'syd', 'Australia/Sydney', 'GMT+11'), 
               ('melbourne', 'mel', 'Australia/Melbourne', 'GMT+11'), 
               ('brisbane', 'bne', 'Australia/Brisbane', 'GMT+10'), 
               ('perth', 'per', 'Australia/Perth', 'GMT+8'), 
               ('adelaide', 'adl', 'Australia/Adelaide', 'GMT+10.5'), 
               ('canberra', 'cbr', 'Australia/Sydney', 'GMT+11')],
        'bangladesh': [('dhaka', 'dac', 'Asia/Dhaka', 'GMT+6')],
        'bd': [('dhaka', 'dac', 'Asia/Dhaka', 'GMT+6')],
        'malaysia': [('kuala lumpur', 'kl', 'Asia/Kuala_Lumpur', 'GMT+8')],
        'my': [('kuala lumpur', 'kl', 'Asia/Kuala_Lumpur', 'GMT+8')],
        'mauritius': [('port louis', 'plu', 'Indian/Mauritius', 'GMT+4')],
        'mu': [('port louis', 'plu', 'Indian/Mauritius', 'GMT+4')],
        'canada': [('toronto', 'yyz', 'America/Toronto', 'GMT-5'), 
                   ('vancouver', 'yvr', 'America/Vancouver', 'GMT-8'), 
                   ('montreal', 'yul', 'America/Toronto', 'GMT-5'), 
                   ('calgary', 'yyc', 'America/Edmonton', 'GMT-7'), 
                   ('ottawa', 'yow', 'America/Toronto', 'GMT-5')],
        'ca': [('toronto', 'yyz', 'America/Toronto', 'GMT-5'), 
               ('vancouver', 'yvr', 'America/Vancouver', 'GMT-8'), 
               ('montreal', 'yul', 'America/Toronto', 'GMT-5'), 
               ('calgary', 'yyc', 'America/Edmonton', 'GMT-7'), 
               ('ottawa', 'yow', 'America/Toronto', 'GMT-5')],
        'unitedstates': [('new york', 'nyc', 'America/New_York', 'GMT-5'), 
                         ('los angeles', 'lax', 'America/Los_Angeles', 'GMT-8'), 
                         ('chicago', 'chi', 'America/Chicago', 'GMT-6'), 
                         ('houston', 'hou', 'America/Chicago', 'GMT-6'), 
                         ('phoenix', 'phx', 'America/Phoenix', 'GMT-7'), 
                         ('seattle', 'sea', 'America/Los_Angeles', 'GMT-8'), 
                         ('miami', 'mia', 'America/New_York', 'GMT-5'),
                         ('atlanta', 'atl', 'America/New_York', 'GMT-5'),
                         ('dallas', 'dfw', 'America/Chicago', 'GMT-6')],
        'us': [('new york', 'nyc', 'America/New_York', 'GMT-5'), 
               ('los angeles', 'lax', 'America/Los_Angeles', 'GMT-8'), 
               ('chicago', 'chi', 'America/Chicago', 'GMT-6'), 
               ('houston', 'hou', 'America/Chicago', 'GMT-6'), 
               ('phoenix', 'phx', 'America/Phoenix', 'GMT-7'), 
               ('seattle', 'sea', 'America/Los_Angeles', 'GMT-8'), 
               ('miami', 'mia', 'America/New_York', 'GMT-5'),
               ('atlanta', 'atl', 'America/New_York', 'GMT-5'),
               ('dallas', 'dfw', 'America/Chicago', 'GMT-6')],
        'england': [('london', 'lon', 'Europe/London', 'GMT+0'), 
                    ('manchester', 'man', 'Europe/London', 'GMT+0'), 
                    ('birmingham', 'bhx', 'Europe/London', 'GMT+0'), 
                    ('liverpool', 'lpl', 'Europe/London', 'GMT+0')],
        'uk': [('london', 'lon', 'Europe/London', 'GMT+0'), 
               ('manchester', 'man', 'Europe/London', 'GMT+0'), 
               ('birmingham', 'bhx', 'Europe/London', 'GMT+0'), 
               ('liverpool', 'lpl', 'Europe/London', 'GMT+0')],
        'germany': [('berlin', 'ber', 'Europe/Berlin', 'GMT+1'), 
                    ('munich', 'muc', 'Europe/Berlin', 'GMT+1'), 
                    ('frankfurt', 'fra', 'Europe/Berlin', 'GMT+1')],
        'ger': [('berlin', 'ber', 'Europe/Berlin', 'GMT+1'), 
                    ('munich', 'muc', 'Europe/Berlin', 'GMT+1'), 
                    ('frankfurt', 'fra', 'Europe/Berlin', 'GMT+1')],
        'france': [('paris', 'par', 'Europe/Paris', 'GMT+1'), 
                   ('lyon', 'lys', 'Europe/Paris', 'GMT+1'), 
                   ('marseille', 'mrs', 'Europe/Paris', 'GMT+1')],
        'fr': [('paris', 'par', 'Europe/Paris', 'GMT+1'), 
                   ('lyon', 'lys', 'Europe/Paris', 'GMT+1'), 
                   ('marseille', 'mrs', 'Europe/Paris', 'GMT+1')],
        'italy': [('rome', 'rom', 'Europe/Rome', 'GMT+1'), 
                  ('milan', 'mil', 'Europe/Rome', 'GMT+1'), 
                  ('naples', 'nap', 'Europe/Rome', 'GMT+1')],
        'it': [('rome', 'rom', 'Europe/Rome', 'GMT+1'), 
                  ('milan', 'mil', 'Europe/Rome', 'GMT+1'), 
                  ('naples', 'nap', 'Europe/Rome', 'GMT+1')],
        'netherlands': [('amsterdam', 'ams', 'Europe/Amsterdam', 'GMT+1'), 
                        ('rotterdam', 'rtm', 'Europe/Amsterdam', 'GMT+1')],
        'nl': [('amsterdam', 'ams', 'Europe/Amsterdam', 'GMT+1'), 
                        ('rotterdam', 'rtm', 'Europe/Amsterdam', 'GMT+1')],
        'denmark': [('copenhagen', 'cph', 'Europe/Copenhagen', 'GMT+1')],
        'dk': [('copenhagen', 'cph', 'Europe/Copenhagen', 'GMT+1')],
        'finland': [('helsinki', 'hel', 'Europe/Helsinki', 'GMT+2')],
        'fi': [('helsinki', 'hel', 'Europe/Helsinki', 'GMT+2')],
        'switzerland': [('zurich', 'zrh', 'Europe/Zurich', 'GMT+1'), 
                        ('geneva', 'gva', 'Europe/Zurich', 'GMT+1')],
        'ch': [('zurich', 'zrh', 'Europe/Zurich', 'GMT+1'), 
                        ('geneva', 'gva', 'Europe/Zurich', 'GMT+1')],
        'luxembourg': [('luxembourg', 'lxm', 'Europe/Luxembourg', 'GMT+1')],
        'lu': [('luxembourg', 'lxm', 'Europe/Luxembourg', 'GMT+1')],
        
    }

    # Normalizing inputs for case-insensitive matching
    from_location = from_location.strip().casefold()
    to_location = to_location.strip().casefold()

    # Gathering entries for source and destination locations
    from_entries = [entry for country, cities in timezones_dict.items() for entry in cities if from_location in {country, entry[0], entry[1]}]
    to_entries = [entry for country, cities in timezones_dict.items() for entry in cities if to_location in {country, entry[0], entry[1]}]

    if not from_entries or not to_entries:
        return [f"**Error:** Could not find timezone information for one of the locations."]

    converted_times = []
    for from_city, _, from_tz, _ in from_entries:
        tz = pytz.timezone(from_tz)
        current_date = datetime.now()  # Get current date
        naive_time = datetime.strptime(time_str, "%I%p").replace(
            year=current_date.year, month=current_date.month, day=current_date.day
        )  # Ensure time includes current date
        aware_time = tz.localize(naive_time)  # Localize to source timezone

        for to_city, _, to_tz, gmt_offset in to_entries:
            target_tz = pytz.timezone(to_tz)
            converted_time = aware_time.astimezone(target_tz)  # Convert to target timezone
            converted_times.append(f"**{time_str}** in {from_city.title()} is **{converted_time.strftime('%I:%M %p')}** in {to_city.title()}, {gmt_offset}")

    return list(set(converted_times))  # Remove duplicates


# Initialize Discord bot with intents - probably should've been at the very top but cuck it we ball
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Placeholder for error logging channel and startup message channel
ERROR_CHANNEL_ID = 1305733544261455882  # error logs
STARTUP_CHANNEL_ID = 1305733544261455882  # channel ID for startup message
PERIODIC_CHANNEL_ID = 1305815351069507604  # Channel to send periodic messages

# startup message
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    # Change the bot's presence
    await client.change_presence(activity=discord.Game(name='time and money.'))

    # Send a startup message to the designated channel
    startup_channel = client.get_channel(STARTUP_CHANNEL_ID)
    if startup_channel:
        await startup_channel.send("Bot has started and is ready to convert currencies!")
    
    # Start background task for periodic messages so Heroku doesn't go bonkers
    client.loop.create_task(send_periodic_message())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Handle 'convert' or variations like 'Convert' and 'conv' (short response)
    if message.content.lower().startswith('convert ') or message.content.lower().startswith('conv '):
        await handle_conversion(message, full_response=False)

    # Handle 'convertfull' or variations like 'Convertfull' and 'convf' (full response)
    elif message.content.lower().startswith('convertfull') or message.content.lower().startswith('convf'):
        await handle_conversion(message, full_response=True)

    # Handle 'chelp' for showing syntax and examples
    elif message.content.lower().startswith('chelp'):
        await message.channel.send(
            "**Currency Conversion Help**\n\n"
            "**1. Basic Conversion:**\n"
            "`conv [amount] [from_currency] to [target_currency]`\n"
            "Example: `conv 100 USD to CAD`\n"
            "Provides a short response with the conversion rate.\n\n"
            "**2. Full Conversion with Details:**\n"
            "`convf [amount] [from_currency] to [target_currency]`\n"
            "Example: `convf 100 USD to CAD`\n"
            "Provides a detailed response including 30-day high, low, average, change, and source link.\n\n"
            
            "Type `clist` to view all supported currencies."
        )
# Add this to the on_message handler to handle the `timez` command
    elif message.content.lower().startswith('time '):
        await handle_time_command(message)

    # Handle 'clist' for listing supported currencies
    elif message.content.lower().startswith('clist'):
        currency_list = "\n".join(
            f"{i+1}. {CURRENCY_NAMES[c][1]} ({c})" for i, c in enumerate(SUPPORTED_CURRENCIES)
        )
        await message.channel.send(
            f"**Supported currencies:**\n{currency_list}\n\n"
            "**To use the currency converter, type:**\n"
            "`conv [amount] [from_currency] to [target_currency]`\n"
            "`convf [amount] [from_currency] to [target currency]` will return more information with source."
        )
# Handle 'cthelp' for listing supported timezones
    elif message.content.lower().startswith('cthelp'):
        await message.channel.send(
            "**time - Current Time:**\n"
            "`time <location>` - Provides the current time in a city or country.\n"
            "Example: `time Kuala Lumpur`, `time MY`, or `time Malaysia`.\n\n"
            "**time @username**\n"
            "`time @username` - Provides the current time for the mentioned user. You have to ping them with @.\n"
            "Example: `time @Zer0`.\n\n"
            "**convt - Time Zone Conversion:**\n"
            "`convt <time> <origin location> to <destination location>` - Converts time from one location to another.\n"
            "Example: `convt 6pm Malaysia to Australia`.\n"
            "If a country has multiple time zones, all zones will be listed; single cities will only show one timezone.\n"
            "**Note:** Minutes are not supported; only hour formats like 6pm or 8am will work.\n\n"
            "All commands are case-_insensitive_.\n"
            "Type `ctlist` to view all supported countries / cities with codes for easy typing."
        )


# Handle 'time' command
    elif message.content.lower().startswith('time '):
        location_name = message.content[5:].strip()
        times = get_current_time(location_name)
        if times:
            # Capitalize only the first letter of each word in the country name
            formatted_times = [
                time.replace(location_name.upper(), location_name.title()) for time in times
            ]
            await message.channel.send("\n".join(formatted_times))
        else:
            await message.channel.send(
                "Timezone(s) unsupported - type 'ctlist' for supported timezones and cities."
            )

    
    elif message.content.lower().startswith('ctlist'):
        response = []  # Initialize response

        for country, cities in sorted(timezones_dict.items()):
         # Get abbreviation from the dictionary, default to blank if not found
                abbreviation = COUNTRY_ABBREVIATIONS.get(country, "")
                country_heading = f"**__{country.title()} ({abbreviation})__**" if abbreviation else f"**__{country.title()}__**"
                response.append(country_heading)

            # Cities with their codes in a single line
                cities_list = ", ".join([f"{city.title()} ({code.upper()})" for city, code, _, _ in sorted(cities)])
                response.append(cities_list)
                response.append("")  # Blank line for readability

    # Send the response as a single message
        await message.channel.send("\n".join(response))

# Handle 'convt' command
    elif message.content.lower().startswith('convt '):
        parts = message.content[6:].split(' to ')
        if len(parts) == 2:
            try:
                time_str, origin_location = parts[0].rsplit(' ', 1)
                destination_location = parts[1].strip()

                converted_times = convert_time(time_str, origin_location, destination_location)

                if converted_times:
                    # Add the country name and ensure GMT is placed at the end
                    formatted_times = []
                    for converted_time in converted_times:
                        # Extract destination city, country, and GMT offset
                        for country, cities in timezones_dict.items():
                            for city, code, _, gmt_offset in cities:
                                if city.lower() == destination_location.lower() or code.lower() == destination_location.lower():
                                    country_name = country.title()
                                    # Correctly format the final output
                                    time_part = converted_time.split(",")[0]  # Extract time part
                                    formatted_times.append(f"{time_part}, {country_name}, {gmt_offset}.")
                                    break
                            else:
                                continue
                            break
                        else:
                            # If no country is found, fallback to original response
                            formatted_times.append(f"{converted_time}.")

                    await message.channel.send("\n".join(formatted_times))
                else:
                    await message.channel.send(
                        "Timezone(s) unsupported - type 'ctlist' for supported timezones and cities."
                    )
            except ValueError:
                await message.channel.send(
                    "Invalid syntax. Use `convt <time> <origin location> to <destination location>`."
                )
        else:
            await message.channel.send(
                "Invalid syntax. Use `convt <time> <origin location> to <destination location>`."
            )


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
                "Timezone(s) unsupported - type 'ctlist' for supported timezones and cities."
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
                f"**That's not a currency dumbfuck. Supported currencies are:**\n{supported_currencies}\n\n"
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
                    f"In the past 30 days, the **high** was {high_30}, the **low** was {low_30}, with an **average** of {average_30} and a **change** of {change_30}%.\n"
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

async def send_periodic_message():
    await client.wait_until_ready()  # Ensure bot is fully ready
    channel = client.get_channel(PERIODIC_CHANNEL_ID)
    while True:
        if channel:
            await channel.send("This is a periodic message sent every 28 minutes. Prevents dynos sleeping on heroku.")
        await asyncio.sleep(28 * 60)  # Wait 28 minutes

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
client.run(DISCORD_TOKEN)
