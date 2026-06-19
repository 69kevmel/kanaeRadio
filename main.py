import os
import discord
import json
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID'))
RADIO_URL = "http://radiomeuh.ice.infomaniak.ch/radiomeuh-128.mp3" 

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

voice_client = None
radio_task = None

async def play_radio(vc):
    global radio_task
    while True:
        # Vérifier s'il reste des utilisateurs dans le salon
        members = [m for m in vc.channel.members if not m.bot]
        if not members:
            print("❌ Plus personne dans le salon, on stop la radio.")
            if vc.is_playing():
                vc.stop()
            await asyncio.sleep(10)
            continue

        if not vc.is_playing():
            source = discord.FFmpegPCMAudio(
                RADIO_URL,
                options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -filter:a "volume=0.3"'
            )
            vc.play(source)
            print("🎶 La radio reprend car quelqu'un est là !")
        await asyncio.sleep(10)

@client.event
async def on_ready():
    print(f"✅ KanaéRadio connecté en tant que {client.user}")

    guild = client.get_guild(GUILD_ID)
    channel = guild.get_channel(VOICE_CHANNEL_ID)

    if channel:
        global voice_client
        voice_client = await channel.connect()
        print(f"🔊 Connecté à {channel.name}")

        global radio_task
        radio_task = asyncio.create_task(play_radio(voice_client))
    else:
        print("❌ Salon vocal introuvable.")

@client.event
async def on_voice_state_update(member, before, after):
    global voice_client
    if voice_client and voice_client.is_connected():
        if after.channel == voice_client.channel or before.channel == voice_client.channel:
            # Si quelqu'un rejoint ou quitte, on relance la vérification du flux
            print("🔄 Mise à jour des états vocaux détectée.")
            # Pas besoin de relancer la task, elle tourne déjà

client.run(TOKEN)
