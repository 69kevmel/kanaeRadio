FROM python:3.11

# Installer FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Installer les dépendances
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt

# Lancer le bot
CMD ["python", "main.py"]
