import os
import discord
from discord.ext import tasks
import logging
import asyncio
import wit_handler as wit
from dotenv import load_dotenv

# Set logging level and initialize tokens and clients.
logging.basicConfig(level=logging.INFO)

logging.info("Booting...")


DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
client = discord.Client()


@client.event
async def on_ready():
    logging.info(f"{client.user} has successfully booted and connected to Discord")
    update_cache.start()

@client.event
async def on_message(message):
    # Limits infinite recursive responses.
    if message.author == client.user:
        return

    # Checks for prefix "Alice" and responds.
    if message.content.lower().startswith("alice"):
        message_clean = message.content.lower().replace("alice ", "")
        async with message.channel.typing():
            resp = wit.get_function(message_clean)
            await asyncio.sleep(0.5)
        await message.channel.send(resp)
    
    # Allows for manual database updates.  Only used for Debug/Development.
    if message.author == "Parkus#2512" and message.content == "A_updateCache":
        async with message.channel.typing():
            await asyncio.sleep(0.5)
        await message.channel.send("Alice will now perform a manual cache update")
        wit.update_cache()
        async with message.channel.typing():
            await asyncio.sleep(0.5)
        await message.channel.send("Alice has finished updating all cached databases")

# Setups automatic cache update.
@tasks.loop(hours=24)
async def update_cache():
    wit.update_cache()

client.run(DISCORD_TOKEN)
