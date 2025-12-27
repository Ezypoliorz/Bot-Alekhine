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
import asyncio
from flask import Flask
from datetime import datetime, date, timedelta, timezone, time
from unidecode import unidecode
import pandas as pd
import re
from dotenv import load_dotenv
import sys
import logging

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
LOGS_CHANNEL_ID = int(os.getenv("LOGS_CHANNEL_ID"))
DEV_BOT_ROLE_ID = int(os.getenv("DEV_BOT_ROLE_ID"))
QUATTRO_ROLE_ID = int(os.getenv("QUATTRO_ROLE_ID"))
TDS_ROLE_ID = int(os.getenv("TDS_ROLE_ID"))
ANNOUNCEMENTS_CHANNEL_ID = int(os.getenv("ANNOUNCEMENTS_CHANNEL_ID"))
TDS_QUATTRO_CHANNEL_ID = int(os.getenv("TDS_QUATTRO_CHANNEL_ID"))
"""RESSOURCES_CHANNEL_ID = int(os.getenv("RESSOURCES_CHANNEL_ID"))"""

with open("départements.json", 'r', encoding="utf-8") as fichier :
    DEPARTEMENTS = json.load(fichier)
    
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

class QuattroReminderView(View) :
    def __init__(self, ronde) :
        super().__init__(timeout=None)
        self.ronde = ronde
    
    @discord.ui.button(
        label="Voir mon match",
        style=discord.ButtonStyle.primary,
        custom_id="quattro_reminder_button",
    )

    async def quattro_reminder_button_callback(self, interaction:discord.Interaction, button:discord.ui.Button) :
        user = interaction.user
        username = user.name
        
        with open("joueurs.json", "r", encoding="utf-8") as fichier :
            joueurs = json.load(fichier)
        
        with open("quattro.json", "r", encoding="utf-8") as fichier :
            quattro = json.load(fichier)
        
        with open("index_joueurs.json", "r", encoding="utf-8") as fichier :
            players_indexes = json.load(fichier)

        player_nom_complet = None
        for joueur_data in joueurs :
            if joueur_data.get("NomDiscord") == username :
                player_nom_complet = joueur_data["NomComplet"]
                break
        
        if player_nom_complet is None :
            embed = discord.Embed(
                    title=f"Vous n'êtes pas trouvé dans la liste des joueurs.",
                    description="Merci de vérifier votre nom Discord. Sinon, expliquez votre problème en mentionnant \"@Dev-bot\"",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        match_found = False
        for poule_name, poule_members in quattro["Appariements"].items() :
            if player_nom_complet in poule_members :
                pairings_ronde = quattro["Matches"][self.ronde]
                embed = discord.Embed(
                    title=f"Votre prochain match de Quattro",
                    color=discord.Color.purple()
                )

                match_a_indices = pairings_ronde[0:2]
                match_b_indices = pairings_ronde[2:4]
                
                player_index_in_poule = poule_members.index(player_nom_complet)

                if player_index_in_poule in match_a_indices :
                    match_indices = match_a_indices
                elif player_index_in_poule in match_b_indices :
                    match_indices = match_b_indices
                else:
                    continue 

                j1_name = poule_members[match_indices[0]]
                j2_name = poule_members[match_indices[1]]
                
                j1_elo = joueurs[players_indexes[j1_name]]["Elo"][:-2]
                j2_elo = joueurs[players_indexes[j2_name]]["Elo"][:-2]
                
                embed.add_field(
                    name=f"{j1_name} ({j1_elo}) - {j2_name} ({j2_elo})",
                    value=f"Ronde {self.ronde+1} du {poule_name}\nDate : {quattro["Dates"][self.ronde]}",
                    inline=False
                )
                
                embed.set_footer(text="Bot Caen Alekhine")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                match_found = True
                return

        if not match_found :
            embed = discord.Embed(
                    title=f"Aucun match trouvé pour vous à cette ronde.",
                    description=f"Merci de vérifier les appariements dans <#{TDS_QUATTRO_CHANNEL_ID}>. Sinon, expliquez votre problème en mentionnant \"@Dev-bot\"",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.response.send_message(embed=embed, ephemeral=True)

@tasks.loop(time=time(hour=9, minute=0, tzinfo=timezone.utc))
async def daily_data_update() :    
    données_ffe.fetch_players()
    données_ffe.fetch_tournaments()
    
    with open("joueurs.json", "r", encoding="utf-8") as fichier :
        players = json.load(fichier)

    guild = bot.get_guild(GUILD_ID)
    if guild :
        for member in guild.members :
            nick = member.nick
            if nick :
                for player in players :
                    if "".join(caractère for caractère in unidecode(player["NomComplet"].upper()) if caractère.isalpha()) == "".join(caractère for caractère in unidecode(nick.upper()) if caractère.isalpha()) :
                        player["NomDiscord"] = member.name
                        break

        with open("joueurs.json", "w", encoding="utf-8") as fichier :
            json.dump(players, fichier, ensure_ascii=False)
    
    with open("tournois.json", "r", encoding="utf-8") as fichier :
        tournaments = json.load(fichier)
    
    channel_announcements = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    channel_tds_quattro = bot.get_channel(TDS_QUATTRO_CHANNEL_ID)
    today = date.today()
    soon_tournaments = []
    posted_tournament_names = set()

    async for message in channel_announcements.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                for field in embed.fields :
                    posted_tournament_names.add(field.name)

    for tournament in tournaments :
        tournament_date = datetime.strptime(tournament["Date"], "%d/%m/%Y").date()
        
        tournament_name_to_check = tournament["NomTournoi"]
        
        if (abs(today - tournament_date) <= timedelta(days=30) and 
            tournament_name_to_check not in posted_tournament_names):
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
                name=f"{tournament["NomTournoi"]}",
                value=f"{tournament["Date"]} • {tournament["Ville"]}\nPlus d'infos : {tournament["LienFiche"]}",
                inline=False
            )
        embed.set_footer(text="Bot Caen Alekhine")
        await channel_announcements.send(embed=embed)

    with open("quattro.json", "r", encoding="utf-8") as fichier :
        quattro = json.load(fichier)
    
    posted_titles = set()

    async for message in channel_tds_quattro.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                posted_titles.add(embed.title)

    for ronde, quattro_date in enumerate(quattro["Dates"]) :
        tournament_date = datetime.strptime(quattro_date, "%d/%m/%Y").date()
        if (abs(today - tournament_date) <= timedelta(days=7) and 
            f"Ronde {ronde+1} de Quattro très bientôt !" not in posted_titles) :
            quattro_reminder_view = QuattroReminderView(ronde=ronde)
            embed = discord.Embed(
                title=f"Ronde {ronde+1} de Quattro très bientôt !",
                description=quattro_date,
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
    
    with open("tds.json", "r", encoding="utf-8") as fichier :
        tds = json.load(fichier)
    
    posted_titles = set()

    async for message in channel_tds_quattro.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                posted_titles.add(embed.title)

    for ronde, tds_date in enumerate(tds["Dates"]) :
        tournament_date = datetime.strptime(tds_date, "%d/%m/%Y").date()
        if (abs(today - tournament_date) <= timedelta(days=7) and 
            f"Ronde {ronde+1} de TDS très bientôt !" not in posted_titles):
            quattro_reminder_view = QuattroReminderView(ronde=ronde)
            embed = discord.Embed(
                title=f"Ronde {ronde+1} de TDS très bientôt !",
                description=quattro_date,
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
        description=f"Connected as {bot.user} - ID : {bot.user.id}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    channel = bot.get_channel(LOGS_CHANNEL_ID)
    await channel.send(embed=embed)

FIRST_START = True
@bot.event
async def on_ready() :
    global FIRST_START
    if not FIRST_START:
        return
    
    """bot.add_view(LinkModerationView())"""
    
    try :
        synced = await tree.sync()
    except Exception as e :
        print(e)
    
    await bot.change_presence(activity=discord.Game(name="Bot du club Caen Alekhine"))

    if not daily_data_update.is_running():
        await daily_data_update()

    FIRST_START = False

def run_server() :
    app = Flask("") 
    
    @app.route("/")
    def home() :
        return "Bot is running and kept alive!"

    port = int(os.environ.get("PORT", 8080))
    
    app.run(host="0.0.0.0", port=port)

"""@bot.event
async def on_member_join(member: discord.Member) :
    channel = bot.get_channel(WELCOME_CHANNEL_ID)

    thread_name = f"Bienvenue, {member.display_name} !"
    thread = await channel.create_thread(
        name=thread_name,
        type=discord.ChannelType.private_thread,
        auto_archive_duration=10080
    )
    await thread.add_user(member)

    embed = discord.Embed(
        title=f"Bienvenue, {member.display_name} !",
        description="Sur le serveur Discord du club d'échecs Caen Alekhine",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Ici, vous pourrez discuter avec les autres membres du club, être averti des prochains tournois,...",
        value="\u200b",
        inline=False
    )
    embed.add_field(
        name="Pour commencer",
        value="Vous pouvez écrire votre nom et prénom ci-dessous, pour que Maël puisse vous donner les permissions nécessaires. Après ça, vous aurez accès au reste du serveur !\nCe processus peut prendre quelques temps, merci de votre patience !\n(Si vous êtes parents d'un enfant membre du club, merci de l'indiquer.)",
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await thread.send(embed=embed)"""

@tree.command(name="ping", description="Répond avec la latence du bot")
@app_commands.default_permissions(administrator=True)
async def ping_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Pong !",
        description=f"Latence : {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

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
        value=f"Vous pouvez interagir avec le bot via des commandes. Pour cela, tapez `/` dans le champ d'envoi de messages, et vous verrez apparaître une fenêtre. En cliquant sur l'icône Bot Alekhine, vous verrez toutes les commandes disponibles :\n`/joueur`\n`/top_10`\n`/tournois`\n`/quattro`\n`/tds`\nCes différentes commandes vous permettent de voir les prochains tournois du Calvados, les tournois internes, les meilleurs joueurs du club,...",
        inline=False
    )
    embed.add_field(
        name=f"Des alertes",
        value=f"N'ayez pas peur de manquer un tournoi ! Des alertes pour les tournois sont envoyées automatiquement, avec les informations importantes.",
        inline=False
    )
    embed.add_field(
        name=f"N'hésitez pas à nous faire part de vos suggestions !",
        value=f"<#1450441585765650472>",
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
async def top_10_command(interaction: discord.Interaction, joueurs : app_commands.Range[int, 1, 25] = 10) :
    with open("joueurs.json", "r", encoding="utf-8") as fichier :
        players = json.load(fichier)
    embed = discord.Embed(
        title=f"Classement Top {joueurs} du Club",
        color=discord.Color.blue()
    )
    number_players = 0
    df = {"Placement" : [], "NomComplet" : [], "ELO" : []}
    for index, player in enumerate(players) :
        if "Actif" in player and player["Actif"] == True :
            embed.add_field(
                name=f"#{number_players+1} • {player["NomComplet"]}",
                value=f"{player["Elo"][:-2]} Elo",
                inline=False
            )
            df["Placement"].append(f"#{number_players+1}")
            df["NomComplet"].append(f"{player["NomComplet"]}")
            df["ELO"].append(f"{player["Elo"]}")
            number_players += 1
        if number_players == joueurs :
            break
    df = pd.DataFrame(df)
    with pd.ExcelWriter(f"Top {joueurs} club.xlsx", engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1", startrow=1, startcol=1)
        
        workbook  = writer.book
        worksheet = writer.sheets["Sheet1"]

        bold_bordure = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 14,
            'font_color': '#3498db',
            'bold': True,
            'align': 'center',
            'border': 1
        })

        bordure = workbook.add_format({
            'font_name': 'Arial',
            'font_size': 14,
            'font_color': 'black',
            'align': 'center',
            'border': 1
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

async def player_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    try:
        with open("index_joueurs.json", "r", encoding="utf-8") as fichier :
            players_indexes = json.load(fichier)
        
        return [
            app_commands.Choice(name=player_name, value=player_name)
            for player_name in players_indexes.keys()
            if current.lower() in player_name.lower()
        ][:25]
    except Exception :
        return []

@tree.command(name="joueur", description="Affiche les infos d'un joueur du club")
@app_commands.describe(joueur="Nom et prénom du joueur")
async def joueur_command(interaction: discord.Interaction, joueur: str):
    await interaction.response.defer()

    with open("joueurs.json", "r", encoding="utf-8") as fichier :
        players = json.load(fichier)
    with open("index_joueurs.json", "r", encoding="utf-8") as fichier :
        players_indexes = json.load(fichier)

    if f"{" ".join(joueur.split(" ")[:-1]).upper()} {joueur.split(" ")[-1]}" in players_indexes :
        player = players[players_indexes[f"{"".join(joueur.split(" ")[:-1]).upper()} {joueur.split(" ")[-1]}"]]
    elif f"{" ".join(joueur.split(" ")[1:]).upper()} {joueur.split(" ")[0]}" in players_indexes :
        player = players[players_indexes[f"{"".join(joueur.split(" ")[1:]).upper()} {joueur.split(" ")[0]}"]]
    else :
        player = données_ffe.search_player("".join(joueur.split(" ")[:-1]).upper(), joueur.split(" ")[-1])
        if player is None :
            player = données_ffe.search_player("".join(joueur.split(" ")[1:]).upper(), joueur.split(" ")[0])
            if player is None :
                embed = discord.Embed(
                    title="Joueur non trouvé",
                    description=f"Aucun joueur enregistré sous le nom : **{joueur}**",
                    color=discord.Color.red()
                )
                embed.set_footer(text="Bot Caen Alekhine")
                await interaction.followup.send(embed=embed)
                return

    embed = discord.Embed(
        title="Fiche Joueur",
        color=discord.Color.blue()
    )
    embed.add_field(name="Nom", value=player["NomComplet"], inline=False)
    
    if "NomDiscord" in player:
        embed.add_field(name="Utilisateur Discord", value=f"@{player['NomDiscord']}", inline=False)
    
    embed.add_field(name="Elo Standard", value=player["Elo"], inline=True)
    embed.add_field(name="Elo Rapide", value=player["Rapide"], inline=True)
    embed.add_field(name="Elo Blitz", value=player["Blitz"], inline=True)
    embed.add_field(name="Club", value=player["Club"], inline=False)
    embed.add_field(name="N° FFE", value=player["NrFFE"], inline=True)
    
    embed.set_footer(text="Bot Caen Alekhine")

    if player.get("FicheFIDE"):
        view = LinkButtonFideView(url=player["FicheFIDE"])
        await interaction.followup.send(embed=embed, view=view)
    else:
        await interaction.followup.send(embed=embed)

@joueur_command.autocomplete("joueur")
async def joueur_auto(interaction: discord.Interaction, current: str) :
    return await player_autocomplete(interaction, current)

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
async def tournois_command(interaction: discord.Interaction, département : str = "14") :
    nom_département = DEPARTEMENTS[département]["Nom"]
    phrase_département = DEPARTEMENTS[département]["Phrase"]
    if département == "14" :
        with open("tournois.json", "r", encoding="utf-8") as fichier :
            tournaments = json.load(fichier)[:25]
    else :
        tournaments = données_ffe.get_tournaments(département)

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
            name=f"{tournament["NomTournoi"]}",
            value=f"{tournament["Date"]} • {tournament["Ville"]}\nPlus d'infos : {tournament["LienFiche"]}",
            inline=False
        )

    embed.set_footer(text="Bot Caen Alekhine")
    link_button_ffe_tournaments_view = LinkButtonFFETournamentsView(url=f"https://www.echecs.asso.fr/ListeTournois.aspx?Action=TOURNOICOMITE&ComiteRef={département}")
    await interaction.response.send_message(embed=embed, view=link_button_ffe_tournaments_view, ephemeral=False)

@tournois_command.autocomplete('département')
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
        with open("quattro.json", "r", encoding="utf-8") as fichier :
            données = json.load(fichier)
        pairings = données["Appariements"]
        options = []
        for quattro in pairings :
            options.append(discord.SelectOption(label=quattro))
            
        dropdown_menu = Select(
            placeholder = "Sélectionnez une poule de Quattro",
            options = options,
            custom_id = "dropdown_menu_quattro"
        )

        dropdown_menu.callback = self.callback_quattro
        return dropdown_menu
    
    async def callback_quattro(self, interaction : discord.Interaction) :
        with open("quattro.json", "r", encoding="utf-8") as fichier :
            données = json.load(fichier)
        pairings = données["Appariements"]
        matches = données["Matches"]
        dates = données["Dates"]
        poule = interaction.data["values"][0]

        await interaction.response.defer()

        embed = discord.Embed(
            title=f"Appariements {poule}",
            color=discord.Color.purple()
        )
        embed.add_field(
            name=f"Joueurs",
            value=f"{pairings[poule][0]} • {pairings[poule][1]} • {pairings[poule][2]} • {pairings[poule][3]}",
            inline=False
        )
        for i in range(6) :
            embed.add_field(
                name=f"Ronde {i+1} • {dates[i]}",
                value=f"{pairings[poule][matches[i][0]]} - {pairings[poule][matches[i][1]]}\n{pairings[poule][matches[i][2]]} - {pairings[poule][matches[i][3]]}",
                inline=False
            )
        
        embed.set_footer(text="Bot Caen Alekhine")

        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=False)

@tree.command(name="quattro", description="Affiche les appariements du Quattro")
async def quattro_command(interaction: discord.Interaction) :
    await interaction.response.send_message("Vous pouvez sélectionner la poule de Quattro qui vous intéresse", ephemeral=True, view=DropdownMenuQuattro())

@tree.command(name="tds", description="Affiche les appariements du TDS")
async def tds_command(interaction: discord.Interaction) :
    with open("tds.json", "r", encoding="utf-8") as fichier :
        tds = json.load(fichier)
    
    embed = discord.Embed(
            title=f"Joueurs TDS",
            color=discord.Color.purple()
        )
    joueurs = ""
    for index, joueur in enumerate(tds["Joueurs"]) :
        joueurs += f"{joueur}\n"
    embed.add_field(
        name = "Joueurs",
        value = joueurs,
        inline=False
    )
    dates = ""
    for index, date in enumerate(tds["Dates"]) :
        dates += f"Ronde {index+1} • {date}\n"
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

"""class LinkModerationView(discord.ui.View) :
    def __init__(self) :
        super().__init__(timeout=None)

    @discord.ui.button(label="Accepter le lien", style=discord.ButtonStyle.success, custom_id="link_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) :
        parts = interaction.message.content.split('\n', 2)
        author_mention = parts[0].replace("Soumission de ", "")
        link = parts[1].replace("Lien : ", "")
        description = parts[2].replace("Description : ", "") if len(parts) > 2 else ""

        public_channel = interaction.guild.get_channel(RESSOURCES_CHANNEL_ID)
        
        embed = discord.Embed(description=description, color=discord.Color.blue())
        embed.set_author(name=f"Partagé par {interaction.user.display_name}")
        embed.add_field(name="Lien", value=link)
        
        await public_channel.send(embed=embed)

        await interaction.response.edit_message(content=f"Accepté par {interaction.user.mention}", view=None, delete_after=30)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger, custom_id="link_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button) :
        await interaction.response.edit_message(content=f"Refusé par {interaction.user.mention}", view=None, delete_after=30)

class LinkSubmitModal(discord.ui.Modal, title='Vérification du lien') :
    def __init__(self, default_text, link) :
        super().__init__()
        self.link = link
        self.link_input = discord.ui.TextInput(
            label='Lien détecté', 
            default=self.link, 
            style=discord.TextStyle.short
        )
        self.desc_input = discord.ui.TextInput(
            label='Description / Message', 
            default=default_text, 
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.link_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction) :
        mod_channel = interaction.guild.get_channel(LOGS_CHANNEL_ID)
        content = f"Soumission de {interaction.user.mention}\nLien : {self.link_input.value}\nDescription : {self.desc_input.value}"
        await mod_channel.send(content=content, view=LinkModerationView())
        await interaction.response.send_message("Lien envoyé en modération, il sera vérifié dès que possible.", ephemeral=True)"""

"""@bot.event
async def on_message(message) :
    if message.author == bot.user :
        return

    if message.channel.id == ANNOUNCEMENTS_CHANNEL_ID :
        urls = re.findall(r'(https?://[^\s]+)', message.content)
        
        if urls :
            found_link = urls[0]
            remaining_text = message.content.replace(found_link, "").strip()
            
            await message.delete()
            
            view = View()
            btn = discord.ui.Button(label="Valider ma publication", style=discord.ButtonStyle.primary)
            
            async def btn_callback(interaction):
                await interaction.response.send_modal(LinkSubmitModal(remaining_text, found_link))
            
            btn.callback = btn_callback
            view.add_item(btn)
            
            await message.channel.send(
                f"{message.author.mention}, votre message contient un lien et doit être vérifié.", view=view, delete_after=30
            )
            return

    await bot.process_commands(message)"""

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) :
    if isinstance(error, app_commands.MissingAnyRole) :
        required_roles = [role for role in error.missing_roles]
        embed = discord.Embed(
            title="Accès refusé",
            description=f"Vous n'avez pas les permissions nécessaires. Vous devez posséder l'un des rôles suivants : {"".join(f"{role}, " for role in required_roles)[:-2]}",
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
            description=f"Merci de bien vouloir réessayer plus tard, nous travaillons à la résolution du problème.",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Bot Caen Alekhine")
        if interaction.response.is_done() :
            await interaction.followup.send(embed=embed, ephemeral=True)
        else :
            await interaction.response.send_message(embed=embed, ephemeral=True)
        embed = discord.Embed(
            title="Une erreur est survenue ",
            description=f"Erreur :\n{error}",
            color=discord.Color.red(),
        )
        channel = bot.get_channel(LOGS_CHANNEL_ID)
        embed.set_footer(text="Bot Caen Alekhine")
        await channel.send(content=f"<@&{DEV_BOT_ROLE_ID}>", embed=embed)
        return

if __name__ == "__main__" :

    t = threading.Thread(target=run_server)
    t.start()

    bot.run(DISCORD_TOKEN)