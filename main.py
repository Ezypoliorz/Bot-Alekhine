import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
import données_ffe
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user} (ID: {bot.user.id})')
    try:
        synced = await tree.sync()
        print(f"Synchronisé")
    except Exception as e:
        print(e)
    await bot.change_presence(activity=discord.Game(name="Bot du club Caen Alekhine"))
    données_ffe.fetch_players()
    données_ffe.fetch_tournaments()
    guild = bot.get_guild(1436057737657192648)
    with open('joueurs.json', 'r', encoding='utf-8') as fichier :
        players = json.load(fichier)
    for member in guild.members :
        nick = member.nick
        if nick :
            for player in players :
                if player["NomComplet"].lower() == nick.lower():
                    player["NomDiscord"] = member.name
                    break
    with open('joueurs.json', 'w', encoding='utf-8') as fichier :
        players = json.dump(players, fichier, ensure_ascii=False)
    print("Prêt !")

class DropdownMenuRole(View) :
    def __init__(self) :
        super().__init__()
        self.add_item(self.create_dropdown())
    
    def create_dropdown(self):
        options = [
            discord.SelectOption(label="Joueur", description="Rejoindre le serveur en tant que joueur du club"),
            discord.SelectOption(label="Parent", description="Rejoindre le serveur en tant que parent d'un joueur du club"),
        ]

        dropdown_menu = Select(
            placeholder = "Quel est votre rôle ?",
            options = options,
            custom_id = "dropdown_menu_role"
        )

        dropdown_menu.callback = self.callback_role
        return dropdown_menu
    
    async def callback_role(self, interaction : discord.interactions) :
        choice = interaction.data["values"][0]
        await interaction.response.send_message(f"Votre rôle : **{choice}**")

@bot.event
async def on_member_join(member: discord.Member) :
    guild = member.guild
    name = member.display_name
    arrival_channel = guild.system_channel
    
    embed = discord.Embed(
        title = f"Bienvenue sur le serveur de Caen Alekhine, {name} !",
        description = "Ceci est un canal d'accueil, où vous pourrez saisir vos informations. Après ça, vous aurez accès à l'entièreté du serveur !",
        color = discord.Color.purple()
    )
    
    await arrival_channel.send(embed=embed)

    message = (
        f"Merci de renseigner votre rôle au club dans la liste déroulante ci-dessous"
    )
    await arrival_channel.send(message, view=DropdownMenuRole())

@tree.command(name="ping", description="Répond avec la latence du bot.")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! Latence : {round(bot.latency * 1000)}ms', ephemeral=False)

@tree.command(name="top_10", description="Affiche le top 10 du club")
async def top_10_command(interaction: discord.Interaction):
    with open("joueurs.json", 'r', encoding='utf-8') as fichier:
        players = json.load(fichier)[:10]
    embed = discord.Embed(
        title="Classement Top 10 du Club",
        color=discord.Color.blue()
    )
    for index, player in enumerate(players) :
        embed.add_field(
            name=f'#{index+1} - {player["NomComplet"]}',
            value=f'{player["Elo"]} Elo',
            inline=False
        )
    embed.set_footer(text="Bot Caen Alekhine")
    embed.set_author(name="Bot Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@tree.command(name="joueur", description="Affiche les infos d'un joueur")
async def joueur_command(interaction: discord.Interaction, nom : str):
    with open("joueurs.json", 'r', encoding='utf-8') as fichier:
        players = json.load(fichier)
    with open("index_joueurs.json", 'r', encoding='utf-8') as fichier:
        players_indexes = json.load(fichier)
    player = players[players_indexes[nom.upper()]]
    embed = discord.Embed(
        title="Info joueur",
        color=discord.Color.green()
    )
    embed.add_field(
        name=f'Nom',
        value=f'{player["NomComplet"]}',
        inline=False
    )
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
        name=f'Catégorie',
        value=f'{player["Cat"]}',
        inline=False
    )
    embed.add_field(
        name=f'N° FFE',
        value=f'{player["NrFFE"]}',
        inline=False
    )
    embed.set_footer(text="Bot Caen Alekhine")
    embed.set_author(name="Bot Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

@tree.command(name="tournois", description="Affiche les prochains tournois")
async def tournois_command(interaction: discord.Interaction):
    with open("tournois.json", 'r', encoding='utf-8') as fichier:
        tournaments = json.load(fichier)[:10]
    embed = discord.Embed(
        title="Prochains tournoi du Calvados",
        color=discord.Color.yellow()
    )
    for index, tournament in enumerate(tournaments) :
        embed.add_field(
            name=f'{tournament["NomTournoi"]}',
            value=f'{tournament["Date"]} - {tournament["Ville"]}',
            inline=False
        )
    embed.set_footer(text="Bot Caen Alekhine")
    embed.set_author(name="Bot Alekhine")
    await interaction.response.send_message(embed=embed, ephemeral=False)

class QuattroButton(discord.ui.View) :
    def __init__(self, timeout=180) :
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Test", style=discord.ButtonStyle.primary, custom_id="quattro_button")
    async def quattro_button_callback(self, interaction : discord.Interaction, button : discord.ui.Button) :
        user = interaction.user

        await interaction.response.send_message(
            await interaction.response.send_message(
                f"{user.display_name}, {user.name}",
                ephemeral=False
            )
        )

@bot.tree.command(name="bouton_test", description="Test")
async def bouton_test_command(interaction: discord.Interaction):
    view_instance = QuattroButton()

    await interaction.response.send_message(
        "Test",
        view=view_instance,
        ephemeral=False
    )

bot.run(os.environ.get('DISCORD_TOKEN'))