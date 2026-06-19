import os
import discord
import asyncio
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

def start_radio(vc):
    """Lance la lecture de la radio."""
    if not vc.is_playing():
        source = discord.FFmpegPCMAudio(
            RADIO_URL,
            options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -filter:a "volume=0.3"'
        )
        vc.play(source)
        print("🎶 La radio reprend car quelqu'un est là !")

async def check_channel_state():
    """Vérifie l'état du salon pour connecter ou déconnecter le bot."""
    global voice_client
    
    guild = client.get_guild(GUILD_ID)
    if not guild:
        return
        
    channel = guild.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        return

    # Lister les membres présents (en excluant les bots)
    members = [m for m in channel.members if not m.bot]

    # 1. Si le salon est VIDE et que le bot est CONNECTÉ
    if not members and voice_client and voice_client.is_connected():
        print("❌ Plus personne dans le salon, déconnexion.")
        await voice_client.disconnect()
        voice_client = None

    # 2. Si le salon n'est PAS VIDE et que le bot est DÉCONNECTÉ
    elif members and (not voice_client or not voice_client.is_connected()):
        print(f"🔊 Connexion à {channel.name}...")
        voice_client = await channel.connect()
        start_radio(voice_client)
        
    # 3. Si le salon n'est PAS VIDE, que le bot est CONNECTÉ mais ne joue pas
    elif members and voice_client and voice_client.is_connected() and not voice_client.is_playing():
        start_radio(voice_client)

@client.event
async def on_ready():
    print(f"✅ KanaéRadio connecté en tant que {client.user}")
    # Vérification de l'état du salon au démarrage du bot
    await check_channel_state()

@client.event
async def on_voice_state_update(member, before, after):
    # On agit uniquement si l'événement concerne le salon vocal de la radio
    if (before.channel and before.channel.id == VOICE_CHANNEL_ID) or \
       (after.channel and after.channel.id == VOICE_CHANNEL_ID):
        
        print("🔄 Mise à jour des états vocaux détectée.")
        await check_channel_state()

client.run(TOKEN)