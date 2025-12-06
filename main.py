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
import asyncio
from unidecode import unidecode

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
GUILD_ID = int(os.environ.get('GUILD_ID'))
LOGS_CHANNEL_ID = int(os.environ.get('LOGS_CHANNEL_ID'))
ROLES_ADMINS = os.environ.get('ROLES_ADMINS').split(',')
WELCOME_CHANNEL_ID = int(os.environ.get('WELCOME_CHANNEL_ID'))
COMMANDS_CHANNEL_ID = int(os.environ.get('COMMANDS_CHANNEL_ID'))
ANNOUNCEMENTS_CHANNEL_ID = int(os.environ.get('ANNOUNCEMENTS_CHANNEL_ID'))
TOURNAMENTS_CHANNEL_ID = int(os.environ.get('TOURNAMENTS_CHANNEL_ID'))
QUATTRO_CHANNEL_ID = int(os.environ.get('QUATTRO_CHANNEL_ID'))
TDS_CHANNEL_ID = int(os.environ.get('TDS_CHANNEL_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
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
        
        with open('joueurs.json', 'r', encoding='utf-8') as fichier :
            joueurs = json.load(fichier)
        
        with open('quattro.json', 'r', encoding='utf-8') as fichier :
            quattro = json.load(fichier)
        
        with open('index_joueurs.json', 'r', encoding='utf-8') as fichier :
            players_indexes = json.load(fichier)

        player_nom_complet = None
        for joueur_data in joueurs :
            if joueur_data.get("NomDiscord") == username :
                player_nom_complet = joueur_data["NomComplet"]
                break
        
        if player_nom_complet is None:
            await interaction.followup.send(
                f"Vous n'êtes pas trouvé dans la liste des joueurs. Vérifiez votre Nom Discord.", 
                ephemeral=True
            )
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

                if player_index_in_poule in match_a_indices:
                    match_indices = match_a_indices
                elif player_index_in_poule in match_b_indices:
                    match_indices = match_b_indices
                else:
                    continue 

                j1_name = poule_members[match_indices[0]]
                j2_name = poule_members[match_indices[1]]
                
                j1_elo = joueurs[players_indexes[j1_name]]['Elo'][:-2]
                j2_elo = joueurs[players_indexes[j2_name]]['Elo'][:-2]
                
                embed.add_field(
                    name=f'{j1_name} ({j1_elo}) - {j2_name} ({j2_elo})',
                    value=f'Ronde {self.ronde+1} du {poule_name}\nDate : {quattro["Dates"][self.ronde]}',
                    inline=False
                )
                
                embed.set_footer(text="Bot Caen Alekhine")
                await interaction.followup.send(embed=embed, ephemeral=True)
                match_found = True
                return

        if not match_found :
             await interaction.response.send_message(
                f"Aucun match n'a été trouvé pour vous dans cette ronde.", 
                ephemeral=True
            )

@tasks.loop(time=time(hour=9, minute=0, tzinfo=timezone.utc))
async def daily_data_update():    
    print("Mise à jour quotidienne des données...")
    
    données_ffe.fetch_players()
    données_ffe.fetch_tournaments()
    
    with open('joueurs.json', 'r', encoding='utf-8') as fichier:
        players = json.load(fichier)

    guild = bot.get_guild(GUILD_ID)
    if guild:
        for member in guild.members:
            nick = member.nick
            if nick:
                for player in players:
                    if ''.join(caractère for caractère in unidecode(player["NomComplet"].upper()) if caractère.isalpha()) == ''.join(caractère for caractère in unidecode(nick.upper()) if caractère.isalpha()):
                        player["NomDiscord"] = member.name
                        break

        with open('joueurs.json', 'w', encoding='utf-8') as fichier :
            json.dump(players, fichier, ensure_ascii=False)
    
    with open('tournois.json', 'r', encoding='utf-8') as fichier :
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
                name=f'{tournament["NomTournoi"]}',
                value=f'{tournament["Date"]} - {tournament["Ville"]}\nPlus d\'infos : {tournament["LienFiche"]}',
                inline=False
            )
        embed.set_footer(text="Bot Caen Alekhine")
        await channel.send(embed=embed)

    with open('quattro.json', 'r', encoding='utf-8') as fichier :
        quattro = json.load(fichier)
    
    posted_titles = set()

    async for message in channel.history(limit=10) :
        if message.author == bot.user :
            for embed in message.embeds :
                posted_titles.add(embed.title)

    for ronde, quattro_date in enumerate(quattro["Dates"]) :
        tournament_date = datetime.strptime(quattro_date, "%d/%m/%Y").date()
        if (abs(today - tournament_date) <= timedelta(days=7) and 
            f"Ronde {ronde+1} de Quattro très bientôt !" not in posted_titles):
            quattro_reminder_view = QuattroReminderView(ronde=ronde)
            embed = discord.Embed(
                title=f"Ronde {ronde+1} de Quattro très bientôt !",
                description=quattro_date,
                color=discord.Color.purple()
            )
            embed.add_field(
                name=f'Merci de prévenir votre adversaire si vous n\'êtes pas disponible !',
                value=f'Si c\'est impossible, prévenir Maël absolument !',
                inline=False
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await channel.send(embed=embed, view=quattro_reminder_view)
            break
    
    with open('tds.json', 'r', encoding='utf-8') as fichier :
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
                name=f'Merci de prévenir votre adversaire si vous n\'êtes pas disponible !',
                value=f'Si c\'est impossible, prévenir Maël absolument !',
                inline=False
            )
            embed.add_field(
                name=f'Appariements',
                value=f'À retrouver dans <#{ANNOUNCEMENTS_CHANNEL_ID}> !',
                inline=False
            )
            embed.set_footer(text="Bot Caen Alekhine")
            await channel.send(embed=embed)
            break

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user} (ID: {bot.user.id})')
    try:
        synced = await tree.sync()
        print(f"Synchronisé")
    except Exception as e:
        print(e)
    
    await bot.change_presence(activity=discord.Game(name="Bot du club Caen Alekhine"))

    if not daily_data_update.is_running():
        await daily_data_update()
    if not daily_data_update.is_running():
        daily_data_update.start()

    print("Bot up and running")
    embed = discord.Embed(
        title="Bot up and running",
        description=f"Connected as {bot.user} - ID: {bot.user.id}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    channel = bot.get_channel(COMMANDS_CHANNEL_ID)
    await channel.send(embed=embed)

def run_server():
    app = Flask('') 
    
    @app.route('/')
    def home():
        return "Bot is running and kept alive!"

    port = int(os.environ.get('PORT', 8080))
    print(f"Démarrage du serveur web sur le port {port}...")
    
    app.run(host='0.0.0.0', port=port)

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
        title=f"🎉 Bienvenue, {member.display_name} !",
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
async def ping_command(interaction: discord.Interaction) :
    embed = discord.Embed(
        title="Pong !",
        description=f"Latence : {round(bot.latency * 1000)}ms",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

@tree.command(name="clear", description="Supprime les derniers messages")
@app_commands.describe(messages="Nombre de messages à supprimer (laisser vide pour vider le salon)")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_any_role(*ROLES_ADMINS)
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
        name=f'Un bot Discord développé pour le club',
        value=f'Intégré au serveur Discord, il a été dévelopé spécialement pour le club Caen Alekhine.',
        inline=False
    )
    embed.add_field(
        name=f'Des commandes',
        value=f'Vous pouvez interagir avec le bot via des commandes. Pour cela, tapez \"/\" dans le champ d\'envoi de messages; vous verrez apparaître une fenêtre. En cliquant sur l\'icône Bot Alekhine, vous verrez toutes les commandes disponibles : `/tournois`, `/quattro`, `/tds`,...\nCes différentes commandes vous permettent de voir les prochains tournois du Calvados, les tournois internes, les meilleurs joueurs du club,...',
        inline=False
    )
    embed.add_field(
        name=f'Des alertes',
        value=f'N\'ayez pas peur de manquer un tournoi ! Des alertes pour les tournois sont envoyées automatiquement, avec les informations importantes.',
        inline=False
    )
    embed.add_field(
        name=f'N\'hésitez pas à nous faire part de vos suggestions !',
        value=f'© Oscar Mazeure',
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

@tree.command(name="top_10", description="Affiche le top 10 du club")
async def top_10_command(interaction: discord.Interaction) :
    with open("joueurs.json", 'r', encoding='utf-8') as fichier:
        players = json.load(fichier)[:10]
    embed = discord.Embed(
        title="Classement Top 10 du Club",
        color=discord.Color.blue()
    )
    for index, player in enumerate(players) :
        embed.add_field(
            name=f'#{index+1} • {player["NomComplet"]}',
            value=f'{player["Elo"][:-2]} Elo',
            inline=False
        )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@tree.command(name="joueur", description="Affiche les infos d'un joueur")
async def joueur_command(interaction: discord.Interaction, nom:str, prénom:str):
    nom = unidecode(nom.upper())
    prénom = unidecode(prénom.upper())
    nom_complet_debut = ''.join(caractère for caractère in nom if caractère.isalpha()) + ''.join(caractère for caractère in prénom if caractère.isalpha())
    with open("joueurs.json", 'r', encoding='utf-8') as fichier:
        players = json.load(fichier)
    with open("index_joueurs.json", 'r', encoding='utf-8') as fichier:
        players_indexes = json.load(fichier)
    nom_complet = None
    for player_index in players_indexes :
        if nom_complet_debut in ''.join(caractère for caractère in unidecode(player_index.upper()) if caractère.isalpha()) :
            nom_complet = player_index
            break
    if nom_complet == None :
        embed = discord.Embed(
            title="Aucun joueur n'est enregistré à ce nom",
            color=discord.Color.red()
        )
        embed.set_footer(text="Bot Caen Alekhine")
        await interaction.response.send_message(embed=embed, ephemeral=False)
        return None
    player = players[players_indexes[nom_complet]] 
    embed = discord.Embed(
        title="Info joueur",
        color=discord.Color.blue()
    )
    embed.add_field(
        name=f'Nom',
        value=f'{player["NomComplet"]}',
        inline=False
    )
    if "NomDiscord" in player :
        embed.add_field(
            name=f'Nom d\'utilisateur Discord',
            value=f'{player["NomDiscord"]}',
            inline=False
        )
    embed.add_field(
        name=f'Elo Standard',
        value=f'{player["Elo"]}',
        inline=False
    )
    embed.add_field(
        name=f'Elo Rapide',
        value=f'{player["Rapide"]}',
        inline=False
    )
    embed.add_field(
        name=f'Elo Blitz',
        value=f'{player["Blitz"]}',
        inline=False
    )
    embed.add_field(
        name=f'N° FFE',
        value=f'{player["NrFFE"]}',
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@tree.command(name="tournois", description="Affiche les prochains tournois")
async def tournois_command(interaction: discord.Interaction):
    with open("tournois.json", 'r', encoding='utf-8') as fichier:
        tournaments = json.load(fichier)[:10]

    if len(tournament) > 0 :
        embed = discord.Embed(
            title="Prochains tournoi du Calvados",
            color=discord.Color.yellow()
        )
        for index, tournament in enumerate(tournaments) :
            embed.add_field(
                name=f'{tournament["NomTournoi"]}',
                value=f'{tournament["Date"]} • {tournament["Ville"]}\nPlus d\'infos : {tournament["LienFiche"]}',
                inline=False
            )
    else :
        embed = discord.Embed(
            title="Aucun tournoi annoncé prochainement",
            description="Plus d'informations sur le site de la FFE : https://www.echecs.asso.fr/ListeTournois.aspx?Action=TOURNOICOMITE&ComiteRef=14",
            color=discord.Color.yellow()
        )

    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

class DropdownMenuQuattro(View) :
    def __init__(self) :
        super().__init__()
        self.add_item(self.create_dropdown())
        
    
    def create_dropdown(self):
        with open("quattro.json", 'r', encoding='utf-8') as fichier :
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
        with open("quattro.json", 'r', encoding='utf-8') as fichier :
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
            name=f'Joueurs',
            value=f'{pairings[poule][0]} • {pairings[poule][1]} • {pairings[poule][2]} • {pairings[poule][3]}',
            inline=False
        )
        for i in range(6) :
            embed.add_field(
                name=f'Ronde {i+1} • {dates[i]}',
                value=f'{pairings[poule][matches[i][0]]} - {pairings[poule][matches[i][1]]}\n{pairings[poule][matches[i][2]]} - {pairings[poule][matches[i][3]]}',
                inline=False
            )
        
        embed.set_footer(text="Bot Caen Alekhine")

        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=False)

@tree.command(name="quattro", description="Affiche les appariements du Quattro")
async def quattro_command(interaction: discord.Interaction) :
    await interaction.response.send_message("Vous pouvez sélectionner la poule de Quattro qui vous intéresse", ephemeral=False, view=DropdownMenuQuattro())

@tree.command(name="tds", description="Affiche la prochaine ronde de TDS")
async def tds_command(interaction: discord.Interaction) :
    with open('tds.json', 'r', encoding='utf-8') as fichier :
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
                name=f'Appariements',
                value=f'À retrouver dans <#{ANNOUNCEMENTS_CHANNEL_ID}> !',
                inline=False
            )

    embed.set_footer(text="Bot Caen Alekhine")
    await interaction.response.send_message(embed=embed)

@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) :
    if isinstance(error, app_commands.MissingAnyRole):
        required_roles = [role.name for role in error.missing_roles]
        embed = discord.Embed(
            title="Accès refusé",
            description=f"Vous n'avez pas les permissions nécessaires. Vous devez posséder l'un des rôles suivants : {''.join(f"{role}, " for role in required_roles)[:-2]}",
            color=discord.Color.red(),
        )
        embed.set_footer(text="Bot Caen Alekhine")
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return

if __name__ == '__main__':

    t = threading.Thread(target=run_server)
    t.start()

    bot.run(DISCORD_TOKEN)