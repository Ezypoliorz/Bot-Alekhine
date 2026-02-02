#   »»» Bot Alekhine «««
#   Bot Discord du club d'échecs Caen Alekhine
#   main.py

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Select, View
import données_ffe
import json
import os
import threading
from flask import Flask, render_template
from datetime import datetime, date, timedelta, timezone, time
from zoneinfo import ZoneInfo
from unidecode import unidecode
import pandas as pd
import re
from dotenv import load_dotenv
import requests
from supabase import create_client, Client, ClientOptions
import asyncio
import logging
import sys
import click

#load_dotenv("Bot-Alekhine Test version.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID"))
DEV_BOT_ROLE_ID = int(os.getenv("DEV_BOT_ROLE_ID"))
QUATTRO_ROLE_ID = int(os.getenv("QUATTRO_ROLE_ID"))
TDS_ROLE_ID = int(os.getenv("TDS_ROLE_ID"))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
TDS_QUATTRO_CHANNEL_ID = int(os.getenv("TDS_QUATTRO_CHANNEL_ID"))
BUG_REPORT_CHANNEL_ID =  int(os.getenv("BUG_REPORT_CHANNEL_ID"))
#RESSOURCES_CHANNEL_ID = int(os.getenv("RESSOURCES_CHANNEL_ID"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
headers_data = ClientOptions(
    headers={
        "User-Agent": "Bot Alekhine",
    }
)
supabase_client : Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=headers_data)

TIMEZONE = ZoneInfo("Europe/Paris")
def timetz(*args) :
    return datetime.now(TIMEZONE).timetuple()

logging.Formatter.converter = timetz

class ColoredFormatter(logging.Formatter):
    GREY = "\x1b[38;20m"
    BLUE = "\x1b[34m"
    ORANGE = "\x1b[33m"
    RED = "\x1b[31m"
    RESET = "\x1b[0m"

    def format(self, record):
        level_colors = {
            logging.INFO: self.BLUE,
            logging.WARNING: self.ORANGE,
            logging.ERROR: self.RED,
            logging.CRITICAL: self.RED
        }
        color = level_colors.get(record.levelno, self.RESET)

        timestamp = self.formatTime(record, self.datefmt)
        
        log_fmt = f"{self.GREY}{timestamp}{self.RESET} {color}[{record.levelname}]{self.RESET} %(message)s"
        
        formatter = logging.Formatter(log_fmt, datefmt=self.datefmt)
        return formatter.format(record)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColoredFormatter(datefmt='%d/%m/%Y %H:%M:%S'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler],
    force=True
)

logger = logging.getLogger(__name__)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

with open("départements.json", "r", encoding="utf-8") as fichier :
    DEPARTEMENTS = json.load(fichier)

CHESS_COM_BASE_URL = "https://api.chess.com/pub"
CHESS_COM_HEADERS = {
    "User-Agent": "Bot Alekhine"
}

LICHESS_BASE_URL = "https://lichess.org/api"
LICHESS_TOKEN = os.getenv("LICHESS_TOKEN")
LICHESS_HEADERS = {
    "Authorization": f"Bearer {LICHESS_TOKEN}",
    "Accept": "application/json"
}
    
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

def send_request(table: str, select_query: str = "*", filters: dict = None, or_logic: str = None, order_by: str = None, desc: bool = False, limit_val: int = None):
    query = supabase_client.table(table).select(select_query)
    
    timestamp = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")
    message = f"Requête GET envoyée à Supabase\n    Table : {table}\n    Sélection : {select_query}"

    if filters :
        message += "\n    Filtres :"
        for column, value in filters.items():
            message += f"\n      {column} : {value} - "
            query = query.eq(column, value)
        message = message[:-2]

    if or_logic:
        message += f"\n    Logique or_ : {or_logic}"
        query = query.or_(or_logic)

    if order_by:
        message += f"\n    Tri : {order_by} ({'DESC' if desc else 'ASC'})"
        query = query.order(order_by, desc=desc)

    if limit_val is not None:
        message += f"\n    Limite : {limit_val}"
        query = query.limit(limit_val)

    logger.info(message)
    
    return query.execute().data

class BotAlekhineError(app_commands.AppCommandError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class QuattroReminderView(View) :
    def __init__(self, ronde=None) :
        super().__init__(timeout=None)
        self.ronde = ronde

    @discord.ui.button(
        label="Voir mon match",
        style=discord.ButtonStyle.primary,
        custom_id="quattro_reminder_button",
    )
    async def quattro_reminder_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button) :
        if self.ronde is None :
            title = interaction.message.embeds[0].title
            self.ronde = int(re.search(r"Ronde (\d+)", title).group(1)) - 1
            
        user = interaction.user
        username = user.name

        players_list = send_request(table="Joueurs",
                                    select_query="id, nom, prénom, elo_standard, classement, actif",
                                    filters={"discord_username" : username})
        
        if len(players_list) == 0 :
            embed = discord.Embed(
                    title=f"Vous n'êtes pas trouvé dans la liste des joueurs",
                    description=f"Merci de vérifier votre nom Discord. Sinon, expliquez votre problème dans <#{BUG_REPORT_CHANNEL_ID}> !",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        else :
            player = players_list[0]

        poules_liste = send_request(table="Poules_Quattro",
                                    select_query="id, nom, joueur_1:Joueurs!Poules_Quattro_joueur_1_fkey(id, nom, prénom, elo_standard), joueur_2:Joueurs!Poules_Quattro_joueur_2_fkey(id, nom, prénom, elo_standard), joueur_3:Joueurs!Poules_Quattro_joueur_3_fkey(id, nom, prénom, elo_standard), joueur_4:Joueurs!Poules_Quattro_joueur_4_fkey(id, nom, prénom, elo_standard)",
                                    or_logic=f"joueur_1.eq.{player["id"]}, joueur_2.eq.{player["id"]}, joueur_3.eq.{player["id"]}, joueur_4.eq.{player["id"]}")

        if len(poules_liste) == 0 :
            embed = discord.Embed(
                    title=f"Vous n'êtes pas trouvé dans les joueurs de Quattro",
                    description=f"Si vous participez au Quattro, merci d'expliquer votre problème dans <#{BUG_REPORT_CHANNEL_ID}> !\n Les appariements sont disponibles dans <#{TDS_QUATTRO_CHANNEL_ID}>.",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        else :
            poule = poules_liste[0]

        matches = send_request(table="Matches Quattro",
                               filters={"id" : self.ronde + 1})
        match = matches[0]

        embed = discord.Embed(
            title=f"Votre prochain match de Quattro",
            color=discord.Color.purple()
        )

        embed.add_field(
            name=f"{poule[match["blancs_1"]]["nom"]} {poule[match["blancs_1"]]["prénom"]} ({poule[match["blancs_1"]]["elo_standard"]}) - {poule[match["noirs_1"]]["nom"]} {poule[match["noirs_1"]]["prénom"]} ({poule[match["noirs_1"]]["elo_standard"]})" if player["id"] in [poule[match["blancs_1"]]["id"], poule[match["noirs_1"]]["id"]] else f"{poule[match["blancs_2"]]["nom"]} {poule[match["blancs_2"]]["prénom"]} ({poule[match["blancs_2"]]["elo_standard"]}) - {poule[match["noirs_2"]]["nom"]} {poule[match["noirs_2"]]["prénom"]} ({poule[match["noirs_2"]]["elo_standard"]})",
            value=f"Ronde {self.ronde+1} du {poule["nom"]}\nDate : **{match["date"]}**",
            inline=False
        )

        embed.set_footer(text="Bot Caen Alekhine")
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(time=time(hour=9, minute=0, tzinfo=TIMEZONE))
async def daily_data_update() :
    timestamp_start = datetime.now(TIMEZONE)
    players = await asyncio.to_thread(données_ffe.fetch_players)
    tournaments = await asyncio.to_thread(données_ffe.fetch_tournaments)

    guild = bot.get_guild(GUILD_ID)
    if guild :
        for member in guild.members :
            nick = member.nick
            if nick :
                for player in players :
                    if "".join(caractère for caractère in unidecode((player["nom"] + player["prénom"]).upper()) if caractère.isalpha()) == "".join(caractère for caractère in unidecode(nick.upper()) if caractère.isalpha()) :
                        player["discord_username"] = member.name
                        player["discord_id"] = member.id
                        break

    supabase_client.table("Joueurs").upsert(players).execute()
    message = f"Requête POST envoyée à Supabase (Table : Joueurs - {len(players)} élements)"
    logger.info(message)

    supabase_client.table("Tournois").upsert(tournaments).execute()
    message = f"Requête POST envoyée à Supabase (Table : Tournois - {len(tournaments)} élements)"
    logger.info(message)

    channel_announcements = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    channel_tds_quattro = bot.get_channel(TDS_QUATTRO_CHANNEL_ID)
    today = date.today()
    soon_tournaments = []
    posted_tournament_names = set()

    async for message in channel_announcements.history(limit=50) :
        if message.author == bot.user :
            for embed in message.embeds :
                for field in embed.fields :
                    posted_tournament_names.add(field.name)

    for tournament in tournaments :
        tournament_date = datetime.strptime(tournament["date"], "%d/%m/%Y").date()
        
        tournament_name_to_check = tournament["nom"]
        
        if tournament_date > today and (abs(today - tournament_date) <= timedelta(days=30) and tournament_name_to_check not in posted_tournament_names) :
            soon_tournaments.append(tournament)
    
    if len(soon_tournaments) != 0 :
        if len(soon_tournaments) == 1 :
            embed = discord.Embed(
                title=f"Nouveau tournoi dans moins d'un mois !",
                color=discord.Color.yellow()
            )
        else :
            embed = discord.Embed(
                title=f"Nouveaux tournois dans moins d'un mois !",
                color=discord.Color.yellow()
            )
        for tournament in soon_tournaments :
            embed.add_field(
                name=f"{tournament["nom"]}",
                value=f"{tournament["date"]} • {tournament["ville"].capitalize()}\nPlus d'infos : `{tournament["url"]}`",
                inline=False
            )
        embed.set_footer(text="Bot Caen Alekhine")
        await channel_announcements.send(embed=embed)

    matches = send_request(table="Matches Quattro")
    
    posted_titles = set()

    async for message in channel_tds_quattro.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                posted_titles.add(embed.title)

    for match in matches :
        tournament_date = datetime.strptime(match["date"], "%d/%m/%Y").date()
        if tournament_date > today and (abs(today - tournament_date) <= timedelta(days=7) and 
            f"Ronde {match["id"]} de Quattro très bientôt !" not in posted_titles) :
            quattro_reminder_view = QuattroReminderView(ronde=match["id"])
            embed = discord.Embed(
                title=f"Ronde {match["id"]} de Quattro très bientôt !",
                description=match["date"],
                color=discord.Color.purple()
            )
            embed.add_field(
                name=f"Merci de prévenir votre adversaire si vous n'êtes pas disponible !",
                value=f"Si c'est impossible, prévenir Maël absolument !",
                inline=False
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await channel_tds_quattro.send(embed=embed, view=quattro_reminder_view, content=f"<@&{QUATTRO_ROLE_ID}>")
            break

    matches = send_request(table="Matches TDS")
    
    posted_titles = set()

    async for message in channel_tds_quattro.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                posted_titles.add(embed.title)

    for match in matches :
        tournament_date = datetime.strptime(match["date"], "%d/%m/%Y").date()
        if tournament_date > today and (abs(today - tournament_date) <= timedelta(days=7) and 
            f"Ronde {match["id"]} de TDS très bientôt !" not in posted_titles):
            quattro_reminder_view = QuattroReminderView(ronde=match["id"])
            embed = discord.Embed(
                title=f"Ronde {match["id"]} de TDS très bientôt !",
                description=match["date"],
                color=discord.Color.purple()
            )
            embed.add_field(
                name=f"Merci de prévenir votre adversaire si vous n'êtes pas disponible !",
                value=f"Si c'est impossible, prévenir Maël absolument !",
                inline=False
            )
            embed.add_field(
                name=f"Appariements",
                value=f"À retrouver dans <#{TDS_QUATTRO_CHANNEL_ID}> !",
                inline=False
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await channel_tds_quattro.send(embed=embed)
            break
    
    embed = discord.Embed(
        title="Bot up and running",
        description=f"Connecté comme {bot.user} - ID : {bot.user.id}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    channel = bot.get_channel(LOGS_CHANNEL_ID)
    await channel.send(embed=embed)
  
    delta = datetime.now(TIMEZONE) - timestamp_start
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    duration = f"{minutes:02}:{seconds:02}"
    logger.info(f"Mise à jour des données effectuée - {duration}")

FIRST_START = True
@bot.event
async def on_ready() :
    global FIRST_START
    if not FIRST_START:
        return

    bot.add_view(QuattroReminderView())

    """bot.add_view(LinkModerationView())"""
    
    try :
        synced = await tree.sync()
    except Exception as e :
        logger.error(e)
    
    await bot.change_presence(activity=discord.Game(name="Bot du club Caen Alekhine"))

    if not daily_data_update.is_running():
        await daily_data_update()
        daily_data_update.start()

    FIRST_START = False

def run_server() :
    app = Flask(__name__) 
    
    @app.route("/")
    def home():
        return render_template("index.html")

    port = int(os.environ.get("PORT", 8080))

    def secho(text, file=None, nl=None, err=None, color=None, **styles):
        pass
    click.echo = secho
    click.secho = secho

    app.run(host="0.0.0.0", port=port)

@tree.command(name="ping", description="Répond avec la latence du bot")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def ping_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Pong !",
        description=f"Latence : **{round(bot.latency * 1000)}ms**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="sync", description="Synchronise et actualise les données du bot")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def sync_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Processus en cours",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=True)
    await daily_data_update()

class ClearValidationView(View) :
    def __init__(self, messages) :
        super().__init__(timeout=None)
        self.messages = messages
        self.limit = messages if messages is None else messages 
        self.message_title = "Nettoyage complet" if messages is None else "Nettoyage partiel"
    
    @discord.ui.button(
        label="Supprimer",
        style=discord.ButtonStyle.danger,
        custom_id="supprimer_clear_button",
    )

    async def supprimer_clear_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button) :
        await interaction.response.defer(ephemeral=True)

        await interaction.delete_original_response()

        deleted = await interaction.channel.purge(limit=self.limit)

        embed = discord.Embed(
            title=self.message_title,
            description=f"{len(deleted)-1 if self.messages is not None else len(deleted)} messages ont été supprimés.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Bot Caen Alekhine")

        try:
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.NotFound :
            await interaction.channel.send(embed=embed, delete_after=5)

@tree.command(name="clear", description="Supprime les derniers messages")
@app_commands.describe(messages="Nombre de messages à supprimer (Laisser vide pour vider le salon)")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def clear_command(interaction: discord.Interaction, messages: app_commands.Range[int, 1, 1000] = None) :    
    await interaction.response.defer(ephemeral=True)

    embed = discord.Embed(
            title=f"Confirmer le nettoyage complet du salon ?" if messages is None else f"Confirmer la suppression de {messages} messages ?",
            color=discord.Color.red()
        )
    embed.set_footer(text="Bot Caen Alekhine")
    clear_validation_view = ClearValidationView(messages=messages)
    await interaction.followup.send(embed=embed, view=clear_validation_view,ephemeral=True)

@tree.command(name="infos", description="Affiche tout ce que vous pouvez faire avec ce bot !")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def infos_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Informations Bot Alekhine",
        color=discord.Color.orange()
    )
    embed.add_field(
        name=f"Un bot Discord développé pour le club",
        value=f"Intégré au serveur Discord, il a été dévelopé spécialement pour le club Caen Alekhine, par des membres du club.",
        inline=False
    )
    embed.add_field(
        name=f"Des commandes",
        value=f"Vous pouvez interagir avec le bot via des commandes. Pour cela, tapez `/` dans le champ d'envoi de messages, et vous verrez apparaître une fenêtre. En cliquant sur l'icône Bot Alekhine, vous verrez toutes les commandes disponibles :\n`/joueur`\n`/top_10`\n`/tournois`\n`/quattro`\n`/tds`\n`/chesscom`\n`/lichess`\n`/puzzle`\nCes différentes commandes vous permettent de voir les prochains tournois du Calvados, les tournois internes, les meilleurs joueurs du club, d'interagir avec Chess.com et Lichess,...",
        inline=False
    )
    embed.add_field(
        name=f"Des alertes",
        value=f"N'ayez pas peur de manquer un tournoi ! Des alertes pour les tournois internes et du Calvados sont envoyées automatiquement, avec les informations importantes.",
        inline=False
    )
    embed.add_field(
        name=f"N'hésitez pas à nous faire part de vos suggestions !",
        value=f"<#{BUG_REPORT_CHANNEL_ID}>",
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

class Top10View(View) :
    def __init__(self, fichier) :
        super().__init__(timeout=None)
        self.filename = fichier
    
    @discord.ui.button(
        label="Exporter en tableau",
        style=discord.ButtonStyle.primary,
        custom_id="top_10_button",
    )

    async def top_10_button_callback(self, interaction:discord.Interaction, button:discord.ui.Button) :
        with open(self.filename, "rb") as f :
            discord_file = discord.File(f, filename=self.filename)
        embed = discord.Embed(
            title="Fichier tableur `xlsx`",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Bot Caen Alekhine")
        await interaction.response.send_message(embed=embed, file=discord_file, ephemeral=True)
        os.remove(self.filename)

@tree.command(name="top_10", description="Affiche le top 10 du club")
@app_commands.describe(joueurs="Nombre de joueurs à afficher (Laisser vide pour le top 10)")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def top_10_command(interaction: discord.Interaction, joueurs : app_commands.Range[int, 1, 25] = 10) :
    players = send_request(table="Joueurs",
                           select_query="nom, prénom, elo_standard, classement, actif",
                           order_by="classement",
                           limit_val=joueurs*2)

    embed = discord.Embed(
        title=f"Classement Top {joueurs} du Club",
        color=discord.Color.blue()
    )
    number_players = 0
    df = {"Placement" : [], "Nom" : [], "ELO" : []}
    for player in players :
        nom_complet = f"{player["nom"].upper()} {player["prénom"].capitalize()}"
        if player["actif"] == True :
            embed.add_field(
                name=f"#{number_players+1} • {nom_complet}",
                value=f"{player["elo_standard"][:-2]} Elo",
                inline=False
            )
            df["Placement"].append(f"#{number_players+1}")
            df["Nom"].append(f"{nom_complet}")
            df["ELO"].append(f"{player["elo_standard"]}")
            number_players += 1
        if number_players == joueurs :
            break
    df = pd.DataFrame(df)
    with pd.ExcelWriter(f"Top {joueurs} club.xlsx", engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=f"Top {joueurs}", startrow=1, startcol=1)
        
        workbook  = writer.book
        worksheet = writer.sheets[f"Top {joueurs}"]

        bold_bordure = workbook.add_format({
            "font_name": "Arial",
            "font_size": 14,
            "font_color": "#3498db",
            "bold": True,
            "align": "center",
            "border": 1
        })

        bordure = workbook.add_format({
            "font_name": "Arial",
            "font_size": 14,
            "font_color": "black",
            "align": "center",
            "border": 1
        })

        worksheet.conditional_format("B2:D2", {"type": "no_errors", "format": bold_bordure})
        worksheet.conditional_format(f"B3:D{2+joueurs}", {"type": "no_errors", "format": bordure})

        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            )
            max_len += 2 + 20/100*max_len

            worksheet.set_column(i+1, i+1, max_len)

    embed.set_footer(text="Bot Caen Alekhine")
    top_10_view = Top10View(fichier=f"Top {joueurs} club.xlsx")
    await interaction.response.send_message(embed=embed, view=top_10_view, ephemeral=False)

class LinkButtonFideView(discord.ui.View) :
    def __init__(self, url) :
        super().__init__(timeout=None)
        
        self.add_item(discord.ui.Button(
            label="Fiche FIDE",
            style=discord.ButtonStyle.link,
            url=url
        ))

@tree.command(name="joueur", description="Affiche les infos d'un joueur du club")
@app_commands.describe(nom="Nom du joueur recherché", prénom="Prénom du joueur recherché")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def joueur_command(interaction: discord.Interaction, nom: str, prénom: str):
    await interaction.response.defer(ephemeral=True)

    prénom = prénom.capitalize()
    nom = nom.upper()

    players = send_request(table="Joueurs",
                           filters={"nom" : nom.upper(), "prénom" : prénom.capitalize()})

    if len(players) == 0 :
        players = données_ffe.search_player(prénom=prénom, nom=nom)
        if len(players) == 0 :
            embed = discord.Embed(
                    title="Joueur non trouvé",
                    description=f"Aucun joueur enregistré sous le nom : **{nom} {prénom}** ",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return                

    for player in players :
        embed = discord.Embed(
            title="Fiche Joueur",
            color=discord.Color.blue()
        )
        embed.add_field(name="Nom", value=f"{nom} {prénom}", inline=False)
        
        if "discord_username" in player:
            embed.add_field(name="Utilisateur Discord", value=f"@{player["discord_username"]}", inline=False)
        
        embed.add_field(name="Elo Standard", value=player["elo_standard"], inline=True)
        embed.add_field(name="Elo Rapide", value=player["elo_rapide"], inline=True)
        embed.add_field(name="Elo Blitz", value=player["elo_blitz"], inline=True)
        if "club" in player :
            embed.add_field(name="Club", value=player["club"], inline=False)
        embed.add_field(name="N° FFE", value=player["id"], inline=True)
        contacts = ""
        if "contact" in player :
            for contact in player["contact"] :
                contacts += f"{contact}\n"
            embed.add_field(name="Contact", value=contacts, inline=False)
        
        embed.set_footer(text="Bot Caen Alekhine")

        if "url_fide" in player :
            view = LinkButtonFideView(url=player["url_fide"])
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)

class LinkButtonFFETournamentsView(discord.ui.View) :
    def __init__(self, url) :
        super().__init__(timeout=None)
        
        self.add_item(discord.ui.Button(
            label="Tournois FFE",
            style=discord.ButtonStyle.link,
            url=url
        ))

@tree.command(name="tournois", description="Affiche les prochains tournois")
@app_commands.describe(département="Département des tournois à rechercher (Laisser vide pour le Calvados)")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def tournois_command(interaction: discord.Interaction, département : str = "14") :
    phrase_département = DEPARTEMENTS[département]["Phrase"]
    if département == "14" :
        tournaments = send_request(table="Tournois",
                                   limit_val=25)
        tournaments.reverse()
    else :
        tournaments = données_ffe.get_tournaments(département)
        tournaments.reverse()
    if len(tournaments) == 1 :
        embed = discord.Embed(
            title=f"Prochain tournoi {phrase_département}",
            color=discord.Color.yellow()
        )
    elif len(tournaments) > 1 :
        embed = discord.Embed(
            title=f"Prochains tournois {phrase_département}",
            color=discord.Color.yellow()
        )
    else :
        embed = discord.Embed(
                title="Aucun tournoi annoncé prochainement",
                description=f"Plus d'informations sur le site de la FFE ci-dessous",
                color=discord.Color.yellow()
            )
    for index, tournament in enumerate(tournaments) :
        embed.add_field(
            name=f"{tournament["nom"]}",
            value=f"{tournament["date"]} • {tournament["ville"].capitalize()}\nPlus d'infos : `{tournament["url"]}`",
            inline=False
        )

    embed.set_footer(text="Bot Caen Alekhine")
    link_button_ffe_tournaments_view = LinkButtonFFETournamentsView(url=f"https://www.echecs.asso.fr/ListeTournois.aspx?Action=TOURNOICOMITE&ComiteRef={département}")
    await interaction.response.send_message(embed=embed, view=link_button_ffe_tournaments_view, ephemeral=False)

@tournois_command.autocomplete("département")
async def dept_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=f"{code} - {nom["Nom"]}", value=code)
        for code, nom in DEPARTEMENTS.items()
        if current.lower() in code.lower() or current.lower() in nom["Nom"].lower()
    ][:25]

class DropdownMenuQuattro(View) :
    def __init__(self) :
        super().__init__()
        self.add_item(self.create_dropdown())
        
    def create_dropdown(self) :
        poules = send_request(table="Joueurs",
                              select_query="id, nom",
                              order_by="id",
                              desc=False)
        options = []
        for poule in poules :
            options.append(discord.SelectOption(label=poule["nom"]))
            
        dropdown_menu = Select(
            placeholder = "Sélectionnez une poule de Quattro",
            options = options,
            custom_id = "dropdown_menu_quattro"
        )

        dropdown_menu.callback = self.callback_quattro
        return dropdown_menu
    
    async def callback_quattro(self, interaction : discord.Interaction) :
        await interaction.response.defer(ephemeral=True)

        poules = send_request(table="Poules_Quattro",
                              select_query="id, nom, joueur_1:Joueurs!Poules_Quattro_joueur_1_fkey(id, nom, prénom), joueur_2:Joueurs!Poules_Quattro_joueur_2_fkey(id, nom, prénom), joueur_3:Joueurs!Poules_Quattro_joueur_3_fkey(id, nom, prénom), joueur_4:Joueurs!Poules_Quattro_joueur_4_fkey(id, nom, prénom)",
                              filters={"nom" : interaction.data["values"][0]})
        poule = poules[0]
        
        matches = send_request(table="Matches Quattro")

        embed = discord.Embed(
            title=f"Appariements du {poule["nom"]}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name=f"Joueurs",
            value=f"{poule["joueur_1"]["nom"]} {poule["joueur_1"]["prénom"]} • {poule["joueur_2"]["nom"]} {poule["joueur_2"]["prénom"]} • {poule["joueur_3"]["nom"]} {poule["joueur_3"]["prénom"]} • {poule["joueur_4"]["nom"]} {poule["joueur_4"]["prénom"]}",
            inline=False
        )
        for match in matches :
            embed.add_field(
                name=f"Ronde {match["id"]} • {match["date"]}",
                value=f"{poule[match["blancs_1"]]["nom"]} {poule[match["blancs_1"]]["prénom"]} - {poule[match["noirs_1"]]["nom"]} {poule[match["noirs_1"]]["prénom"]}\n{poule[match["blancs_2"]]["nom"]} {poule[match["blancs_2"]]["prénom"]} - {poule[match["noirs_2"]]["nom"]} {poule[match["noirs_2"]]["prénom"]}",
                inline=False
            )
        
        embed.set_footer(text="Bot Caen Alekhine")

        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=False)

@tree.command(name="quattro", description="Affiche les appariements du Quattro")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def quattro_command(interaction: discord.Interaction) :
    await interaction.response.send_message("Vous pouvez sélectionner la poule de Quattro qui vous intéresse", ephemeral=True, view=DropdownMenuQuattro())

@tree.command(name="tds", description="Affiche les appariements du TDS")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def tds_command(interaction: discord.Interaction) :
    joueurs = send_request(table="Joueurs_TDS",
                           select_query="id, joueur:Joueurs!Joueurs_TDS_joueur_fkey(id, nom, prénom)")

    matches = send_request(table="Matches TDS")

    embed = discord.Embed(
            title=f"Joueurs TDS",
            color=discord.Color.purple()
        )
    liste_joueurs = ""
    for joueur in joueurs :
        liste_joueurs += f"{joueur["joueur"]["nom"]} {joueur["joueur"]["prénom"]}\n"
    embed.add_field(
        name = "Joueurs",
        value = liste_joueurs,
        inline=False
    )
    dates = ""
    for match in matches :
        dates += f"Ronde {match["id"]} • {match["date"]}\n"
    embed.add_field(
        name = "Dates",
        value = dates,
        inline=False
    )
    embed.add_field(
                name=f"Appariements",
                value=f"À retrouver dans <#{TDS_QUATTRO_CHANNEL_ID}> !",
                inline=False
            )

    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

@tree.command(name="puzzle", description="Affiche le problème du jour de Chess.com")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def puzzle_command(interaction: discord.Interaction) :
    await interaction.response.defer(ephemeral=True)
    headers = {"User-Agent": "Bot Alekhine"}
    response = requests.get("https://api.chess.com/pub/puzzle", headers=headers)
    if response.status_code == 200 :
        data = response.json()
        image = data.get("image")
        title = data.get("title")
        pgn_text = data.get("pgn")

        move_section = pgn_text.split("\r\n\r\n")[-1]
        solution = move_section.replace("*", "").strip()
        solution = solution.replace("K", "R").replace("Q", "D").replace("N", "C").replace("B", "F").replace("R", "T")

        embed = discord.Embed(
            title=f"Problème du jour",
            description=f"\"{title}\"",
            color=discord.Color.pink()
        )
        embed.add_field(
            name = f"Solution : ||{solution}||",
            value = "Source : Chess.com",
            inline=False
        )
        embed.set_image(url=image)
        embed.set_footer(text="Bot Caen Alekhine")
        await interaction.followup.send(embed=embed, ephemeral=False)

class LinkButtonOnlineProfileView(discord.ui.View) :
    def __init__(self, url, plateforme) :
        super().__init__(timeout=None)
        
        self.add_item(discord.ui.Button(
            label=f"Profil {plateforme}",
            style=discord.ButtonStyle.link,
            url=url
        ))

@tree.command(name="chesscom", description="Affichez les infos d'un compte Chess.com")
@app_commands.describe(utilisateur="Nom d'utilisateur recherché")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def chesscom_command(interaction: discord.Interaction, utilisateur:str) :
    await interaction.response.defer(ephemeral=True)

    url = f"{CHESS_COM_BASE_URL}/player/{utilisateur}"
    response = requests.get(url, headers=CHESS_COM_HEADERS)
    infos = response.json()

    if "code" in infos :
        if infos["code"] == 0 :
            embed = discord.Embed(
                    title="Utilisateur non trouvé",
                    description=f"Aucun joueur enregistré sous le nom d'utilisateur : **{utilisateur}** ",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        else :
            raise BotAlekhineError(str(infos))

    url = f"{CHESS_COM_BASE_URL}/player/{utilisateur}/stats"
    response = requests.get(url, headers=CHESS_COM_HEADERS)
    stats = response.json()

    description = f":flag_{infos["country"][-2:].lower()}: {infos["name"]}"
    if "title" in infos :
        description += f" - **{infos["title"]}**"

    embed = discord.Embed(
        title=utilisateur,
        description = description,
        color=discord.Color.pink()
    )
    embed.add_field(
        name="Rapide",
        value=f"{stats["chess_rapid"]["last"]["rating"]} Elo\nRecord : {stats["chess_rapid"]["best"]["rating"]}",
        inline=True
    )
    embed.add_field(
        name="Blitz",
        value=f"{stats["chess_blitz"]["last"]["rating"]} Elo\nRecord : {stats["chess_blitz"]["best"]["rating"]}",
        inline=True
    )
    embed.add_field(
        name="Bullet",
        value=f"{stats["chess_bullet"]["last"]["rating"]} Elo\nRecord : {stats["chess_bullet"]["best"]["rating"]}",
        inline=True
    )
    embed.add_field(
        name="Différé",
        value=f"{stats["chess_daily"]["last"]["rating"]} Elo\nRecord : {stats["chess_daily"]["best"]["rating"]}",
        inline=True
    )
    embed.add_field(
        name="Problèmes",
        value=f"Record : {stats["tactics"]["highest"]["rating"]} Elo",
        inline=True
    )
    if infos["is_streamer"] == True :
        streams = "Streame sur "
        urls = ""
        for streaming_platform in infos["streaming_platforms"] :
            streams += f"{streaming_platform["type"].capitalize()}, "
            urls += f"`{streaming_platform["channel_url"]}`\n"
        streams = streams[:-2]
        embed.add_field(
            name=streams,
            value=urls,
            inline=False
        )
    if infos["league"] :
        embed.add_field(
            name="Ligue",
            value=infos["league"],
            inline=False
        )

    if "avatar" in infos :
        embed.set_thumbnail(url=infos["avatar"])
    else :
        embed.set_thumbnail(url="https://www.chess.com/bundles/web/images/user-image.007dad08.svg")
    embed.set_footer(text="Bot Caen Alekhine")
    chesscom_view = LinkButtonOnlineProfileView(infos["url"], "Chess.com")
    await interaction.followup.send(embed=embed, view=chesscom_view, ephemeral=False)

@tree.command(name="lichess", description="Affichez les infos d'un compte Lichess")
@app_commands.describe(utilisateur="Nom d'utilisateur recherché")
@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
async def lichess_command(interaction: discord.Interaction, utilisateur:str) :
    await interaction.response.defer(ephemeral=True)

    url = f"{LICHESS_BASE_URL}/user/{utilisateur}"
    response = requests.get(url, headers=LICHESS_HEADERS)
    infos = response.json()

    if "error" in infos :
        if infos["error"] == "Not found" :
            embed = discord.Embed(
                    title="Utilisateur non trouvé",
                    description=f"Aucun joueur enregistré sous le nom d'utilisateur : **{utilisateur}** ",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        else :
            raise BotAlekhineError(infos["error"])

    if "profile" in infos :
        description = ""
        if "flag" in infos["profile"] :
            description += f":flag_{infos["profile"]["flag"].lower()}: "
        if "realName" in infos["profile"] :
            description += f"{infos["profile"]["realName"]} "
        if "title" in infos :
            description += f"- **{infos["title"]}**" if len(description) > 0 else f"**{infos["title"]}**"

    embed = discord.Embed(
        title=utilisateur,
        description = description,
        color=discord.Color.pink()
    )
    embed.add_field(
        name="Rapide",
        value=f"{infos["perfs"]["rapid"]["rating"]} Elo",
        inline=True
    )
    embed.add_field(
        name="Blitz",
        value=f"{infos["perfs"]["blitz"]["rating"]} Elo",
        inline=True
    )
    embed.add_field(
        name="Bullet",
        value=f"{infos["perfs"]["bullet"]["rating"]} Elo",
        inline=True
    )
    embed.add_field(
        name="Classique",
        value=f"{infos["perfs"]["classical"]["rating"]} Elo",
        inline=True
    )
    embed.add_field(
        name="Correspondance",
        value=f"{infos["perfs"]["correspondence"]["rating"]} Elo",
        inline=True
    )
    embed.add_field(
        name="Problèmes",
        value=f"{infos["perfs"]["puzzle"]["rating"]} Elo",
        inline=True
    )

    embed.set_footer(text="Bot Caen Alekhine")
    lichess_view = LinkButtonOnlineProfileView(infos["url"], "Lichess")
    await interaction.followup.send(embed=embed, view=lichess_view, ephemeral=False)

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: app_commands.Command):
    log_channel = bot.get_channel(LOGS_CHANNEL_ID)  
    timestamp = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M:%S")

    message = f"[{timestamp}] @{interaction.user.name} - **/{interaction.command.name}**"

    if "options" in interaction.data :
        message += " ("
        for option in interaction.data["options"] :
            message += f"{option['name']} : {option['value']} - "
        message = f"{message[:-3]})"

    await log_channel.send(message)
    logger.info(message.replace("*", "").split("] ")[1])

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) :
    if isinstance(error, app_commands.MissingAnyRole) :
        required_roles = [role for role in error.missing_roles]
        embed = discord.Embed(
            title="Utilisation de la commande refusée",
            description=f"Vous n'avez pas les permissions nécessaires. Vous devez posséder l'un des rôles suivants : {"".join(f"{role}, " for role in required_roles)[:-2]}\nSi vous êtes censé y avoir accès, merci d'expliquer votre problème dans <@&{BUG_REPORT_CHANNEL_ID}> !",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Bot Caen Alekhine")
        if interaction.response.is_done() :
            await interaction.followup.send(embed=embed, ephemeral=True)
        else :
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    else :
        embed = discord.Embed(
            title="Une erreur est survenue",
            description=f"Merci de bien vouloir réessayer plus tard, nous travaillons à la résolution du problème.\nVous pouvez donner des détails sur le problème dans <#{BUG_REPORT_CHANNEL_ID}> !",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Bot Caen Alekhine")
        if interaction.response.is_done() :
            await interaction.followup.send(embed=embed, ephemeral=True)
        else :
            await interaction.response.send_message(embed=embed, ephemeral=True)
        channel = bot.get_channel(LOGS_CHANNEL_ID)
        message = error.message if isinstance(error, app_commands.BotAlekhine) else error
        embed = discord.Embed(
            title="Une erreur est survenue ",
            description=f"**Erreur :**\n{message}",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Bot Caen Alekhine")
        await channel.send(content=f"<@&{DEV_BOT_ROLE_ID}>", embed=embed)
        logger.error(message)
        return
        
@bot.event
async def on_guild_join(guild) :
    if guild.id != GUILD_ID :
        try :
            channel = guild.system_channel or next((x for x in guild.text_channels if x.permissions_for(guild.me).send_messages), None)
            if channel :
                await channel.send("L'utiisation de ce bot est réservée au serveur Discord du club d'échecs Caen Alkhine. Il va donc immédiatement être retiré de ce serveur.\nThe use of this bot is reserved to the Discord server for the Caen Alekhine chess club. It will now automatically be removed from this server.")
        except Exception :
            pass
        
        await guild.leave()
        channel = bot.get_channel(LOGS_CHANNEL_ID)
        await channel.send(f"Le bot a quitté un serveur Discord non autorisé ({guild.name} - {guild.id})")
        logger.warning(f"Le bot a quitté un serveur Discord non autorisé ({guild.name} - {guild.id})")

@bot.check
async def is_in_authorized_guild(ctx) :
    if ctx.guild and ctx.guild.id == GUILD_ID :
        return True
    return False

if __name__ == "__main__" :

    t = threading.Thread(target=run_server)
    t.start()

    bot.run(DISCORD_TOKEN, log_handler=None)