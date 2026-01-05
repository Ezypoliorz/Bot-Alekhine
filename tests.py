import requests
from dotenv import load_dotenv
import os

CHESS_COM_BASE_URL = "https://api.chess.com/pub"
CHESS_COM_HEADERS = {
    "User-Agent": "Bot Alekhine"
}

utilisateur = "grehgieruhgiuerh"

url = f"{CHESS_COM_BASE_URL}/player/{utilisateur}"
response = requests.get(url, headers=CHESS_COM_HEADERS)
infos = response.json()

url = f"{CHESS_COM_BASE_URL}/player/{utilisateur}/stats"
response = requests.get(url, headers=CHESS_COM_HEADERS)
stats = response.json()

print(infos)
print(stats)