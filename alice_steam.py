import requests
from dotenv import load_dotenv
import random
import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
load_dotenv('.env')

# Handles raw message output from Wit.ai API and responds using responses.json.
def steam_function(meaning, responses):
    # Set variables for easy access
    intent = meaning['intents'][0]['name']
    entities = meaning['entities']
    traits = meaning['traits']
    game_title = entities['game_title:game_title'][0]['body'].title()
    r = ""
    # Find appids for apps with similar titles to game_title.
    app_id = name_to_id(game_title)
    # Checks if no similar titles were found.
    if app_id == None:
        response = responses["steam"]["unsuccessful"]
    # If appids were found, execute functions depending on intent of raw message output from Wit.ai.
    else:
        if intent == 'get_price':
            r = get_price(app_id)
            if r == None:
                response = responses["steam"]["get_price"]["none"] 
            else:
                response = responses["steam"]["get_price"]["general"]  
        if intent == 'get_dlc':
            r = get_dlc(app_id)
            if r == None:
                if "polar_question" in traits:
                    response = responses["steam"]["get_dlc"]["polar"]["no"]
                else:
                    response = responses["steam"]["get_dlc"]["none"]
            else:
                if "polar_question" in traits:
                    response = responses["steam"]["get_dlc"]["polar"]["yes"]      
                if "request" in traits:
                    response = responses["steam"]["get_dlc"]["request"]     
                if "inquiry" in traits:
                    response = responses["steam"]["get_dlc"]["inquiry"]
                if "command" in traits:
                    response = responses["steam"]["get_dlc"]["command"]   
        if intent == 'get_page':
            r = get_page(app_id)
            if "command" in traits:
                response = responses["steam"]["get_page"]["command"]   
            elif "inquiry" in traits:
                response = responses["steam"]["get_page"]["inquiry"]
        if intent == 'is_on_sale':
            r = is_on_sale(app_id)
            if r == None:
                response = responses["steam"]["is_on_sale"]["none"]    
            else:  
                if r[0] == "0%":
                    response = responses["steam"]["is_on_sale"]["polar"]["no"]     
                else:
                    response = responses["steam"]["is_on_sale"]["polar"]["yes"]    
        if intent == 'release_date':
            r = release_date(app_id)
            response = responses["steam"]["release_date"]
        if intent == 'supported_platforms':
            r = supported_platforms(app_id)    
            if "target_platform:target_platform" in entities:
                if entities["target_platform:target_platform"]["body"] in r:
                    response = responses["steam"]["supported_platforms"]["targeted"]["true"]    
            else:
                response = responses["steam"]["supported_platforms"]["general"]
    # Shuffle responses so responses are more varied.
    random.shuffle(response)
    return response[0].format(game_title = game_title, r = r)
    

# Updates applist.db with up to date applist from Steam Web API.
def steam_cache():
    # Establishes connection to applist.db.
    logging.info("Now updating database...")
    logging.info("Connecting to database...")
    conn = sqlite3.connect("applist.db")
    db = conn.cursor()
    
    # Creates apps table if it doesn't exist already.
    logging.info("Checking for initial cache...")
    db.execute("CREATE TABLE IF NOT EXISTS 'apps' ('appid' integer PRIMARY KEY NOT NULL, 'name' text);")

    # Retrieves applist from Steam database
    logging.info("Retrieving applist from Steam database")
    applist = requests.get("https://api.steampowered.com/ISteamApps/GetAppList/v2/").json()
    
    # Inserts every app listing into local database
    logging.info("Creating cache...")
    for app in applist['applist']['apps']:
        db.execute("INSERT OR REPLACE INTO apps (appid, name) VALUES (?, ?)", (app['appid'], app['name']))
        print(app['appid'], app['name'])
    conn.commit()
    conn.close()
    logging.info("Database update complete")

# Takes name and returns appid from database in applist.db
def name_to_id(name):
    # Establishes connection to applist.db
    conn = sqlite3.connect("applist.db")
    conn.row_factory = lambda cursor, row: row[0]
    db = conn.cursor()
    # Splits name on spaces into list to make parsing easier.
    name_parsed = name.split()  
    # Sets SQL search statement depending on length of title.
    if len(name_parsed) == 1:
        db_search = "SELECT appid FROM apps WHERE name LIKE ?"
    else:
        first_term = "name LIKE ?||'%' AND "
        search_term = " AND ".join(["name LIKE '%'||?||'%'"] * (len(name_parsed) - 1))
        db_search = "SELECT appid FROM apps WHERE " + first_term + search_term
    # Searches database using search statement and returns.
    app_id = db.execute(db_search, tuple(name_parsed)).fetchall()
    if not app_id:
        return None
    return app_id

# Takes appids and returns price for first game in list.
def get_price(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        # Checks if appid is a game.
        if r[str(app)]["data"]["type"] == "game":
            # CHecks if game does not have a price (i.e. free or unreleased).
            if "price_overview" not in r[str(app)]["data"]:
                return(None)
            # Returns formatted price of game if found.
            result = r[str(app)]["data"]["price_overview"]['final_formatted']
            return(result)

# Takes appids and returns any DLC found for the first game in list.
def get_dlc(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        # Checks if appid is a game.
        if r[str(app)]["data"]["type"] == "game":
            # Checks if game does not have any dlc.
            if "dlc" not in r[str(app)]["data"]:
                return None
            # Creates a list of appids of all DLCs found for the game.
            dlcs = r[str(app)]["data"]["dlc"]
            break
    # Initialize lists for name and price of each DLC.
    name = []
    price = []
    # Makes calls to Steam API for each dlc and stores values within lists.
    for dlc in dlcs:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': dlc}).json()
        name.append(r[str(dlc)]["data"]["name"])
        # Checks if DLC does not have a price (i.e. free or unreleased).
        if "price_overview" not in r[str(dlc)]["data"]:
            price.append("N/A")
        # Adds formatted price of DLC to list if found.
        else:
            price.append(r[str(dlc)]["data"]["price_overview"]["final_formatted"])
    # Zips lists into dictionary for easy access and parsing.
    tmp = dict(zip(name, price))
    # Formats dictionary into string format to insert into response.
    result = ""
    for name, price in tmp.items():
        result += f"{name}:    {price}\n"
    return result

# Takes appids and returns steam page for first game in list.
def get_page(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        if r[str(app)]["data"]["type"] == "game":
            result = "https://store.steampowered.com/app/" + str(app)
            return result

# Takes appids and checks if first game in list is on sale.
def is_on_sale(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        if r[str(app)]["data"]["type"] == "game":
            # Checks if game does not have a price (i.e. free or unreleased).
            if "price_overview" not in r[str(app)]["data"]:
                return(None)
            # Formats API response into list for easy access and parsing.
            result = []
            result.append(str(r[str(app)]["data"]["price_overview"]['discount_percent']) + '%')
            result.append(r[str(app)]["data"]["price_overview"]['initial_formatted'])
            result.append(r[str(app)]["data"]["price_overview"]['final_formatted'])
            return(result)

# Takes appids and returns the release date for the first game in list.
def release_date(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        if r[str(app)]["data"]["type"] == "game":
            # Checks for special case 'coming soon'.
            if r[str(app)]["data"]["release_date"]['coming_soon'] == True:
                return "Coming soon"
            # Formats release date into list for easy access and parsing.
            result = r[str(app)]["data"]["release_date"]['date'].split()
            return(result)

# Takes appids and returns supported platforms for the first game in list.
def supported_platforms(app_id):
    for app in app_id:
        r = requests.get("http://store.steampowered.com/api/appdetails/", params={'appids': app}).json()    
        if r[str(app)]["data"]["type"] == "game":
            supported = r[str(app)]["data"]["platforms"]
            # Formats API response into list for easy access and parsing.
            result = []
            for platform, available in supported.items():
                if available:
                    result.append(platform)
            # Formats response depending on list length
            if len(result) == 3:
                return "all platforms" 
            elif len(result) == 2:
                return " and ".join(result)
            elif len(result) == 1:
                return result[0]
