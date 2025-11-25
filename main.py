import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
import données_ffe
import json
import os
import threading
from flask import Flask

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
    print("🟢 Bot up and running")
    embed = discord.Embed(
        title="🟢 Bot up and running",
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot Caen Alekhine")
    channel = bot.get_channel(1436057794725023824)
    await channel.send(embed=embed)

def run_server():
    app = Flask('') 
    
    @app.route('/')
    def home():
        return "Bot is running and kept alive!"

    port = int(os.environ.get('PORT', 8080))
    print(f"Démarrage du serveur web sur le port {port}...")
    
    app.run(host='0.0.0.0', port=port)

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
            value=f'{player["Elo"][:-2]} Elo',
            inline=False
        )
    embed.set_footer(text="Bot Caen Alekhine")
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
            color=discord.Color.orange()
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
async def quattro_command(interaction: discord.Interaction):
    await interaction.response.send_message("Vous pouvez sélectionner la poule de Quattro qui vous intéresse", ephemeral=False, view=DropdownMenuQuattro())

if __name__ == '__main__':

    t = threading.Thread(target=run_server)
    t.start()

    bot.run(os.environ.get('DISCORD_TOKEN'))