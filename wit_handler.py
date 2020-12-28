import os
import alice_steam
import json
import random
from wit import Wit
from dotenv import load_dotenv

# Initialize tokens and clients.
load_dotenv('.env')
WIT_TOKEN = os.getenv('WIT_TOKEN')
wit = Wit(WIT_TOKEN)

# Import responses.
with open('responses.json') as file:
    responses = json.load(file)

# Categorizes raw message output from Wit.ai API using traits from output
def get_function(message):
    meaning = wit.message(message)
    traits = meaning['traits']
    steam = first_value(traits, 'steam')

    if steam:
        response = alice_steam.steam_function(meaning, responses)
        return response

# Checks if specified trait is in output 
def first_value(obj, key):
    if key not in obj:
        return None
    val = obj[key][0]['value']
    if not val:
        return None
    return val

# Returns raw message output from Wit.ai.  Only used for Debug/Development.
def get_raw(message):
    meaning = wit.message(message)
    return meaning

# Manual cache update to be called from main.py
def update_cache():
    alice_steam.steam_cache()