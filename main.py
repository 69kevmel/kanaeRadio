import os
import discord
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration des logs structurés
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('kanaé_radio.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID'))
RADIO_URL = "http://radiomeuh.ice.infomaniak.ch/radiomeuh-128.mp3"
INACTIVITY_TIMEOUT = 300  # 5 minutes en secondes
CHECK_INTERVAL = 20  # Vérification toutes les 20 secondes (optimisation CPU)

# Intents minimalistes pour économiser la bande passante
intents = discord.Intents.default()
intents.voice_states = True  # Nécessaire pour on_voice_state_update

client = discord.Client(intents=intents)

voice_client = None
radio_task = None
last_activity_time = None
reconnect_attempts = 0
MAX_RECONNECT_ATTEMPTS = 5


def log_info(message):
    """Log un message d'information"""
    logger.info(f"ℹ️  {message}")


def log_success(message):
    """Log un message de succès"""
    logger.info(f"✅ {message}")


def log_error(message):
    """Log un message d'erreur"""
    logger.error(f"❌ {message}")


def log_warning(message):
    """Log un message d'avertissement"""
    logger.warning(f"⚠️  {message}")


async def play_radio(vc):
    """Boucle principale de lecture radio avec gestion d'inactivité"""
    global last_activity_time, reconnect_attempts
    
    log_info("Démarrage de la boucle de lecture radio")
    last_activity_time = datetime.now()
    last_member_count = 0  # Éviter les logs répétitifs
    
    while True:
        try:
            # Vérifier si le bot est toujours connecté
            if not vc or not vc.is_connected():
                log_error("Déconnecté du salon vocal, arrêt de la boucle")
                break

            # Obtenir les utilisateurs non-bot du salon
            members = [m for m in vc.channel.members if not m.bot]
            now = datetime.now()
            time_since_activity = (now - last_activity_time).total_seconds()

            # Cas 1 : Personne dans le salon
            if not members:
                # Seul log si le nombre de personnes a changé
                if last_member_count > 0:
                    log_info(f"Salon vide - timeout dans {INACTIVITY_TIMEOUT - int(time_since_activity)}s")
                    last_member_count = 0
                
                # Arrêter la radio si elle joue
                if vc.is_playing():
                    vc.stop()
                    log_info("Radio arrêtée")

                # Vérifier le timeout de 5 minutes
                if time_since_activity >= INACTIVITY_TIMEOUT:
                    log_warning("Timeout d'inactivité atteint, déconnexion")
                    await vc.disconnect()
                    break
                
                await asyncio.sleep(CHECK_INTERVAL)
                continue

            # Cas 2 : Des utilisateurs sont présents
            if len(members) != last_member_count:
                log_success(f"{len(members)} utilisateur(s) connecté(s)")
                last_member_count = len(members)
            
            # Toujours réinitialiser le timer s'il y a des utilisateurs
            last_activity_time = now

            # Lancer la radio si elle n'est pas en cours
            if not vc.is_playing():
                try:
                    source = discord.FFmpegPCMAudio(
                        RADIO_URL,
                        options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -filter:a "volume=0.5"'
                    )
                    vc.play(source)
                    log_success("Radio en lecture")
                    reconnect_attempts = 0
                except Exception as e:
                    log_error(f"Erreur FFmpeg: {type(e).__name__}")
                    await asyncio.sleep(5)
                    continue

            await asyncio.sleep(CHECK_INTERVAL)

        except asyncio.CancelledError:
            log_warning("Boucle radio annulée")
            break
        except Exception as e:
            log_error(f"Erreur dans play_radio: {type(e).__name__}")
            await asyncio.sleep(CHECK_INTERVAL)


async def ensure_bot_in_voice_channel(guild, channel):
    """S'assurer que le bot est connecté au salon vocal"""
    global voice_client, radio_task
    
    if voice_client and voice_client.is_connected():
        return voice_client
    
    try:
        log_info(f"Tentative de connexion à {channel.name}")
        voice_client = await channel.connect()
        log_success(f"Connecté au salon {channel.name}")
        
        # Lancer la tâche de radio
        if radio_task is None or radio_task.done():
            radio_task = asyncio.create_task(play_radio(voice_client))
            log_info("Tâche de radio créée")
        
        return voice_client
    except discord.Forbidden:
        log_error("Permission refusée pour se connecter au salon vocal")
        return None
    except discord.DiscordException as e:
        log_error(f"Erreur Discord: {type(e).__name__} - {str(e)}")
        return None
    except Exception as e:
        log_error(f"Erreur inattendueà la connexion: {type(e).__name__} - {str(e)}")
        return None


@client.event
async def on_ready():
    """Événement de connexion du bot"""
    log_success(f"KanaéRadio connecté en tant que {client.user}")

    try:
        guild = client.get_guild(GUILD_ID)
        if not guild:
            log_error(f"Serveur avec l'ID {GUILD_ID} introuvable")
            return

        channel = guild.get_channel(VOICE_CHANNEL_ID)
        if not channel:
            log_error(f"Salon vocal avec l'ID {VOICE_CHANNEL_ID} introuvable")
            return

        # Mettre à jour le statut du bot
        await client.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="Kanaé Radio 🎙️")
        )
        
        await ensure_bot_in_voice_channel(guild, channel)

    except Exception as e:
        log_error(f"Erreur lors de l'initialisation: {type(e).__name__} - {str(e)}")


@client.event
async def on_voice_state_update(member, before, after):
    """Détecte les changements d'état vocal (connexion/déconnexion)"""
    global voice_client
    
    try:
        # Ignorer les changements du bot lui-même
        if member.bot:
            return

        guild = member.guild
        channel = guild.get_channel(VOICE_CHANNEL_ID)

        if not channel:
            return

        # Cas 1 : Quelqu'un rejoins le salon radio
        if after.channel and after.channel.id == VOICE_CHANNEL_ID:
            log_info(f"{member.name} a rejoint le salon")
            
            # S'assurer que le bot est connecté
            if not voice_client or not voice_client.is_connected():
                log_warning("Bot pas connecté, reconnexion...")
                await ensure_bot_in_voice_channel(guild, channel)
            
            # Réinitialiser le timer d'inactivité
            global last_activity_time
            last_activity_time = datetime.now()

        # Cas 2 : Quelqu'un quitte le salon radio
        elif before.channel and before.channel.id == VOICE_CHANNEL_ID:
            log_info(f"{member.name} a quitté le salon")

    except Exception as e:
        log_error(f"Erreur dans on_voice_state_update: {type(e).__name__} - {str(e)}")


@client.event
async def on_disconnect():
    """Événement de déconnexion du bot"""
    global voice_client, radio_task
    
    log_warning("Bot déconnecté de Discord")
    
    # Annuler la tâche de radio
    if radio_task and not radio_task.done():
        radio_task.cancel()
        try:
            await radio_task
        except asyncio.CancelledError:
            pass
        log_info("Tâche de radio annulée")

    # Déconnecter du salon vocal
    if voice_client and voice_client.is_connected():
        try:
            await voice_client.disconnect()
            log_success("Déconnecté du salon vocal")
        except Exception as e:
            log_error(f"Erreur lors de la déconnexion: {type(e).__name__} - {str(e)}")


@client.event
async def on_error(event, *args, **kwargs):
    """Gestion globale des erreurs"""
    log_error(f"Erreur dans l'événement {event}")


if __name__ == "__main__":
    try:
        log_info("Démarrage de KanaéRadio...")
        client.run(TOKEN)
    except KeyboardInterrupt:
        log_warning("Arrêt manuel du bot")
    except Exception as e:
        log_error(f"Erreur fatale: {type(e).__name__} - {str(e)}")

