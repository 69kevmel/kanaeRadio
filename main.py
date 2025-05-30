import discord
import asyncio
import os

TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))  # ID de ton serveur Discord
VOICE_CHANNEL_ID =  int(os.getenv('VOICE_CHANNEL_ID'))  # ID du salon vocal
RADIO_URL = "http://radiomeuh.ice.infomaniak.ch/radiomeuh-128.mp3" 

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ KanaéRadio connecté en tant que {client.user}")

    guild = client.get_guild(GUILD_ID)
    channel = guild.get_channel(VOICE_CHANNEL_ID)

    if channel:
        voice = await channel.connect()
        print(f"🔊 Connecté à {channel.name}")

        while True:
            if not voice.is_playing():
                source = discord.FFmpegPCMAudio(RADIO_URL, options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -filter:a "volume=0.3"')
                voice.play(source)
            await asyncio.sleep(10)


@client.event
async def on_disconnect():
    print("❌ KanaéRadio déconnecté.")

client.run(TOKEN)
