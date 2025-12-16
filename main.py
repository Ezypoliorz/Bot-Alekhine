import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Select, View
import données_ffe
import json
import os
import sys
import threading
from flask import Flask
from datetime import datetime, date, timedelta, timezone, time
from unidecode import unidecode

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = int(os.environ.get("GUILD_ID"))
LOGS_CHANNEL_ID = int(os.environ.get("LOGS_CHANNEL_ID"))
DEV_BOT_ID = int(os.environ.get("DEV_BOT_ID"))
WELCOME_CHANNEL_ID = int(os.environ.get("WELCOME_CHANNEL_ID"))
COMMANDS_CHANNEL_ID = int(os.environ.get("COMMANDS_CHANNEL_ID"))
ANNOUNCEMENTS_CHANNEL_ID = int(os.environ.get("ANNOUNCEMENTS_CHANNEL_ID"))
TOURNAMENTS_CHANNEL_ID = int(os.environ.get("TOURNAMENTS_CHANNEL_ID"))
QUATTRO_CHANNEL_ID = int(os.environ.get("QUATTRO_CHANNEL_ID"))
TDS_CHANNEL_ID = int(os.environ.get("TDS_CHANNEL_ID"))

DEPARTEMENTS = {
    "01": {"Nom": "Ain", "Phrase": "dans l'Ain"},
    "02": {"Nom": "Aisne", "Phrase": "dans l'Aisne"},
    "03": {"Nom": "Allier", "Phrase": "dans l'Allier"},
    "04": {"Nom": "Alpes-de-Haute-Provence", "Phrase": "dans les Alpes-de-Haute-Provence"},
    "05": {"Nom": "Hautes-Alpes", "Phrase": "dans les Hautes-Alpes"},
    "06": {"Nom": "Alpes-Maritimes", "Phrase": "dans les Alpes-Maritimes"},
    "07": {"Nom": "Ardèche", "Phrase": "dans l'Ardèche"},
    "08": {"Nom": "Ardennes", "Phrase": "dans les Ardennes"},
    "09": {"Nom": "Ariège", "Phrase": "dans l'Ariège"},
    "10": {"Nom": "Aube", "Phrase": "dans l'Aube"},
    "11": {"Nom": "Aude", "Phrase": "dans l'Aude"},
    "12": {"Nom": "Aveyron", "Phrase": "dans l'Aveyron"},
    "13": {"Nom": "Bouches-du-Rhône", "Phrase": "dans les Bouches-du-Rhône"},
    "14": {"Nom": "Calvados", "Phrase": "au Calvados"},
    "15": {"Nom": "Cantal", "Phrase": "dans le Cantal"},
    "16": {"Nom": "Charente", "Phrase": "en Charente"},
    "17": {"Nom": "Charente-Maritime", "Phrase": "en Charente-Maritime"},
    "18": {"Nom": "Cher", "Phrase": "dans le Cher"},
    "19": {"Nom": "Corrèze", "Phrase": "en Corrèze"},
    "2A": {"Nom": "Corse-du-Sud", "Phrase": "en Corse-du-Sud"},
    "2B": {"Nom": "Haute-Corse", "Phrase": "en Haute-Corse"},
    "21": {"Nom": "Côte-d'Or", "Phrase": "en Côte-d'Or"},
    "22": {"Nom": "Côtes-d'Armor", "Phrase": "dans les Côtes-d'Armor"},
    "23": {"Nom": "Creuse", "Phrase": "en Creuse"},
    "24": {"Nom": "Dordogne", "Phrase": "en Dordogne"},
    "25": {"Nom": "Doubs", "Phrase": "dans le Doubs"},
    "26": {"Nom": "Drôme", "Phrase": "en Drôme"},
    "27": {"Nom": "Eure", "Phrase": "dans l'Eure"},
    "28": {"Nom": "Eure-et-Loir", "Phrase": "en Eure-et-Loir"},
    "29": {"Nom": "Finistère", "Phrase": "dans le Finistère"},
    "30": {"Nom": "Gard", "Phrase": "dans le Gard"},
    "31": {"Nom": "Haute-Garonne", "Phrase": "en Haute-Garonne"},
    "32": {"Nom": "Gers", "Phrase": "dans le Gers"},
    "33": {"Nom": "Gironde", "Phrase": "en Gironde"},
    "34": {"Nom": "Hérault", "Phrase": "dans l'Hérault"},
    "35": {"Nom": "Ille-et-Vilaine", "Phrase": "en Ille-et-Vilaine"},
    "36": {"Nom": "Indre", "Phrase": "dans l'Indre"},
    "37": {"Nom": "Indre-et-Loire", "Phrase": "en Indre-et-Loire"},
    "38": {"Nom": "Isère", "Phrase": "en Isère"},
    "39": {"Nom": "Jura", "Phrase": "dans le Jura"},
    "40": {"Nom": "Landes", "Phrase": "dans les Landes"},
    "41": {"Nom": "Loir-et-Cher", "Phrase": "dans le Loir-et-Cher"},
    "42": {"Nom": "Loire", "Phrase": "dans la Loire"},
    "43": {"Nom": "Haute-Loire", "Phrase": "en Haute-Loire"},
    "44": {"Nom": "Loire-Atlantique", "Phrase": "en Loire-Atlantique"},
    "45": {"Nom": "Loiret", "Phrase": "dans le Loiret"},
    "46": {"Nom": "Lot", "Phrase": "dans le Lot"},
    "47": {"Nom": "Lot-et-Garonne", "Phrase": "dans le Lot-et-Garonne"},
    "48": {"Nom": "Lozère", "Phrase": "en Lozère"},
    "49": {"Nom": "Maine-et-Loire", "Phrase": "en Maine-et-Loire"},
    "50": {"Nom": "Manche", "Phrase": "dans la Manche"},
    "51": {"Nom": "Marne", "Phrase": "dans la Marne"},
    "52": {"Nom": "Haute-Marne", "Phrase": "en Haute-Marne"},
    "53": {"Nom": "Mayenne", "Phrase": "en Mayenne"},
    "54": {"Nom": "Meurthe-et-Moselle", "Phrase": "en Meurthe-et-Moselle"},
    "55": {"Nom": "Meuse", "Phrase": "dans la Meuse"},
    "56": {"Nom": "Morbihan", "Phrase": "dans le Morbihan"},
    "57": {"Nom": "Moselle", "Phrase": "en Moselle"},
    "58": {"Nom": "Nièvre", "Phrase": "en Nièvre"},
    "59": {"Nom": "Nord", "Phrase": "dans le Nord"},
    "60": {"Nom": "Oise", "Phrase": "dans l'Oise"},
    "61": {"Nom": "Orne", "Phrase": "dans l'Orne"},
    "62": {"Nom": "Pas-de-Calais", "Phrase": "dans le Pas-de-Calais"},
    "63": {"Nom": "Puy-de-Dôme", "Phrase": "dans le Puy-de-Dôme"},
    "64": {"Nom": "Pyrénées-Atlantiques", "Phrase": "dans les Pyrénées-Atlantiques"},
    "65": {"Nom": "Hautes-Pyrénées", "Phrase": "dans les Hautes-Pyrénées"},
    "66": {"Nom": "Pyrénées-Orientales", "Phrase": "dans les Pyrénées-Orientales"},
    "67": {"Nom": "Bas-Rhin", "Phrase": "dans le Bas-Rhin"},
    "68": {"Nom": "Haut-Rhin", "Phrase": "dans le Haut-Rhin"},
    "69": {"Nom": "Rhône", "Phrase": "dans le Rhône"},
    "70": {"Nom": "Haute-Saône", "Phrase": "en Haute-Saône"},
    "71": {"Nom": "Saône-et-Loire", "Phrase": "en Saône-et-Loire"},
    "72": {"Nom": "Sarthe", "Phrase": "dans la Sarthe"},
    "73": {"Nom": "Savoie", "Phrase": "en Savoie"},
    "74": {"Nom": "Haute-Savoie", "Phrase": "en Haute-Savoie"},
    "75": {"Nom": "Paris", "Phrase": "à Paris"},
    "76": {"Nom": "Seine-Maritime", "Phrase": "en Seine-Maritime"},
    "77": {"Nom": "Seine-et-Marne", "Phrase": "en Seine-et-Marne"},
    "78": {"Nom": "Yvelines", "Phrase": "dans les Yvelines"},
    "79": {"Nom": "Deux-Sèvres", "Phrase": "dans les Deux-Sèvres"},
    "80": {"Nom": "Somme", "Phrase": "dans la Somme"},
    "81": {"Nom": "Tarn", "Phrase": "dans le Tarn"},
    "82": {"Nom": "Tarn-et-Garonne", "Phrase": "dans le Tarn-et-Garonne"},
    "83": {"Nom": "Var", "Phrase": "dans le Var"},
    "84": {"Nom": "Vaucluse", "Phrase": "dans le Vaucluse"},
    "85": {"Nom": "Vendée", "Phrase": "en Vendée"},
    "86": {"Nom": "Vienne", "Phrase": "dans la Vienne"},
    "87": {"Nom": "Haute-Vienne", "Phrase": "en Haute-Vienne"},
    "88": {"Nom": "Vosges", "Phrase": "dans les Vosges"},
    "89": {"Nom": "Yonne", "Phrase": "dans l'Yonne"},
    "90": {"Nom": "Territoire de Belfort", "Phrase": "dans le Territoire de Belfort"},
    "91": {"Nom": "Essonne", "Phrase": "en Essonne"},
    "92": {"Nom": "Hauts-de-Seine", "Phrase": "dans les Hauts-de-Seine"},
    "93": {"Nom": "Seine-Saint-Denis", "Phrase": "en Seine-Saint-Denis"},
    "94": {"Nom": "Val-de-Marne", "Phrase": "dans le Val-de-Marne"},
    "95": {"Nom": "Val-d'Oise", "Phrase": "dans le Val-d'Oise"}
}

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
            await interaction.followup.send(embed=embed, ephemeral=True)
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
                await interaction.followup.send(embed=embed, ephemeral=True)
                match_found = True
                return

        if not match_found :
            embed = discord.Embed(
                    title=f"Aucun match trouvé pour vous à cette ronde.",
                    description="Merci de vérifier les appariements dans <#{ANNOUNCEMENTS_CHANNEL_ID}>. Sinon, expliquez votre problème en mentionnant \"@Dev-bot\"",
                    color=discord.Color.red()
                )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.followup.send(embed=embed, ephemeral=True)

@tasks.loop(time=time(hour=9, minute=0, tzinfo=timezone.utc))
async def daily_data_update() :    
    print("Mise à jour quotidienne des données...")
    
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
    
    channel = bot.get_channel(TOURNAMENTS_CHANNEL_ID)
    today = date.today()
    soon_tournaments = []
    posted_tournament_names = set()

    async for message in channel.history(limit=10) :
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
        await channel.send(embed=embed)

    with open("quattro.json", "r", encoding="utf-8") as fichier :
        quattro = json.load(fichier)
    
    posted_titles = set()

    async for message in channel.history(limit=10) :
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
            await channel.send(embed=embed, view=quattro_reminder_view)
            break
    
    with open("tds.json", "r", encoding="utf-8") as fichier :
        tds = json.load(fichier)
    
    posted_titles = set()

    async for message in channel.history(limit=10) :
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
                value=f"À retrouver dans <#{ANNOUNCEMENTS_CHANNEL_ID}> !",
                inline=False
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await channel.send(embed=embed)
            break

@bot.event
async def on_ready() :
    try :
        synced = await tree.sync()
    except Exception as e :
        print(e)
    
    await bot.change_presence(activity=discord.Game(name="Bot du club Caen Alekhine"))

    if not daily_data_update.is_running() :
        await daily_data_update()
    if not daily_data_update.is_running() :
        daily_data_update.start()

    embed = discord.Embed(
        title="Bot up and running",
        description=f"Connected as {bot.user} - ID : {bot.user.id}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    channel = bot.get_channel(COMMANDS_CHANNEL_ID)
    await channel.send(embed=embed)

def run_server() :
    app = Flask("") 
    
    @app.route("/")
    def home() :
        return "Bot is running and kept alive!"

    port = int(os.environ.get("PORT", 8080))
    
    app.run(host="0.0.0.0", port=port)

@bot.event
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
    await thread.send(embed=embed)

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

@tree.command(name="clear", description="Supprime les derniers messages")
@app_commands.describe(messages="Nombre de messages à supprimer (Laisser vide pour vider le salon)")
@app_commands.default_permissions(administrator=True)
async def clear_command(interaction: discord.Interaction, messages: app_commands.Range[int, 1, 1000] = None) :
    if messages is None :
        limit = None
        message_title = "Nettoyage complet"
    else :
        limit = messages + 1
        message_title = "Nettoyage partiel"
    
    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=limit)

    embed = discord.Embed(
        title=message_title,
        description=f"{len(deleted)-1 if messages is not None else len(deleted)} messages ont été supprimés.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.followup.send(embed=embed, ephemeral=True)

@tree.command(name="infos", description="Affiche tout ce que vous pouvez faire avec ce bot !")
async def infos_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Informations Bot Alekhine",
        color=discord.Color.orange()
    )
    embed.add_field(
        name=f"Un bot Discord développé pour le club",
        value=f"Intégré au serveur Discord, il a été dévelopé spécialement pour le club Caen Alekhine, par des membres du club",
        inline=False
    )
    embed.add_field(
        name=f"Des commandes",
        value=f"Vous pouvez interagir avec le bot via des commandes. Pour cela, tapez \"/\" dans le champ d'envoi de messages; vous verrez apparaître une fenêtre. En cliquant sur l'icône Bot Alekhine, vous verrez toutes les commandes disponibles :\n`/joueur`\n`/top_10`\n`/tournois`\n`/quattro`\n`/tds`\nCes différentes commandes vous permettent de voir les prochains tournois du Calvados, les tournois internes, les meilleurs joueurs du club,...",
        inline=False
    )
    embed.add_field(
        name=f"Des alertes",
        value=f"N'ayez pas peur de manquer un tournoi ! Des alertes pour les tournois sont envoyées automatiquement, avec les informations importantes.",
        inline=False
    )
    embed.add_field(
        name=f"N'hésitez pas à nous faire part de vos suggestions !",
        value=f"© Oscar Mazeure",
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

@tree.command(name="top_10", description="Affiche le top 10 du club")
@app_commands.describe(joueurs="Nombre de joueurs à afficher (Laisser vide pour le top 10)")
async def top_10_command(interaction: discord.Interaction, joueurs : app_commands.Range[int, 1, 25] = 10) :
    with open("joueurs.json", "r", encoding="utf-8") as fichier :
        players = json.load(fichier)
    embed = discord.Embed(
        title="Classement Top 10 du Club",
        color=discord.Color.blue()
    )
    number_players = 0
    for index, player in enumerate(players) :
        if "Actif" in player and player["Actif"] == True :
            embed.add_field(
                name=f"#{number_players+1} • {player["NomComplet"]}",
                value=f"{player["Elo"][:-2]} Elo",
                inline=False
            )
            number_players += 1
        if number_players == joueurs :
            break
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

class LinkButtonFideView(discord.ui.View) :
    def __init__(self, url) :
        super().__init__(timeout=None)
        
        self.add_item(discord.ui.Button(
            label="Fiche FIDE",
            style=discord.ButtonStyle.link,
            url=url
        ))

@tree.command(name="joueur", description="Affiche les infos d'un joueur")
@app_commands.describe(nom="Nom de famille du joueur recherché")
@app_commands.describe(prénom="Prénom du joueur recherché")
async def joueur_command(interaction: discord.Interaction, nom:str, prénom:str) :
    nom = unidecode(nom.upper())
    prénom = unidecode(prénom.upper())
    nom_complet_debut = "".join(caractère for caractère in nom if caractère.isalpha()) + "".join(caractère for caractère in prénom if caractère.isalpha())
    with open("joueurs.json", "r", encoding="utf-8") as fichier :
        players = json.load(fichier)
    with open("index_joueurs.json", "r", encoding="utf-8") as fichier :
        players_indexes = json.load(fichier)
    nom_complet = None
    for player_index in players_indexes :
        if nom_complet_debut in "".join(caractère for caractère in unidecode(player_index.upper()) if caractère.isalpha()) :
            nom_complet = player_index
            break
    if nom_complet == None :
        player = données_ffe.search_player(nom, prénom)
        if player is None :
            embed = discord.Embed(
                title="Aucun joueur n'est enregistré à ce nom",
                color=discord.Color.red()
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return None
    else :
        player = players[players_indexes[nom_complet]]
    embed = discord.Embed(
        title="Info joueur",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f"Nom",
        value=f"{player["NomComplet"]}",
        inline=False
    )
    if "NomDiscord" in player :
        embed.add_field(
            name=f"Nom d'utilisateur Discord",
            value=f"{player["NomDiscord"]}",
            inline=False
        )
    embed.add_field(
        name=f"Elo Standard",
        value=f"{player["Elo"]}",
        inline=False
    )
    embed.add_field(
        name=f"Elo Rapide",
        value=f"{player["Rapide"]}",
        inline=False
    )
    embed.add_field(
        name=f"Elo Blitz",
        value=f"{player["Blitz"]}",
        inline=False
    )
    embed.add_field(
        name=f"Club",
        value=f"{player["Club"]}",
        inline=False
    )
    embed.add_field(
        name=f"N° FFE",
        value=f"{player["NrFFE"]}",
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    if player["FicheFIDE"] :
        link_button_fide_view = LinkButtonFideView(url=player["FicheFIDE"])
        await interaction.response.send_message(embed=embed, view=link_button_fide_view, ephemeral=False)
    else :
        await interaction.response.send_message(embed=embed, ephemeral=False)

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
            title=f"Prochain tournoi dans {phrase_département}",
            color=discord.Color.yellow()
        )
    elif len(tournaments) > 1 :
        embed = discord.Embed(
            title=f"Prochains tournois dans {phrase_département}",
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
        app_commands.Choice(name=f"{code} - {nom}", value=code)
        for code, nom in DEPARTEMENTS.items()
        if current.lower() in code.lower() or current.lower() in nom.lower()
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
@app_commands.default_permissions(administrator=True)
async def quattro_command(interaction: discord.Interaction) :
    await interaction.response.send_message("Vous pouvez sélectionner la poule de Quattro qui vous intéresse", ephemeral=False, view=DropdownMenuQuattro())

@tree.command(name="tds", description="Affiche la prochaine ronde de TDS")
@app_commands.default_permissions(administrator=True)
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
                value=f"À retrouver dans <#{ANNOUNCEMENTS_CHANNEL_ID}> !",
                inline=False
            )

    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

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
        await channel.send(content=f"<@&{DEV_BOT_ID}>", embed=embed)
        return

if __name__ == "__main__" :

    t = threading.Thread(target=run_server)
    t.start()

    bot.run(DISCORD_TOKEN)