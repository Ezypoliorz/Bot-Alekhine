import requests
from bs4 import BeautifulSoup
from operator import itemgetter
import json
import datetime
import re
from unidecode import unidecode

URL_CLUB = 'https://www.echecs.asso.fr/ListeJoueurs.aspx?Action=JOUEURCLUBREF&ClubRef=184'
PAYLOAD_CONSTANTES = {
    '__EVENTTARGET': 'ctl00$ContentPlaceHolderMain$PagerFooter', 
    '__VIEWSTATEGENERATOR': '37C7F7E6',
}

URL_FFE = "https://www.echecs.asso.fr/ListeTournois.aspx?Action=TOURNOICOMITE&ComiteRef=14"
BASE_URL = "https://www.echecs.asso.fr/"
ABBR_MONTH_MAP = {
    'janv': 1, 'févr': 2, 'mars': 3, 'avr': 4,
    'mai': 5, 'juin': 6, 'juil': 7, 'août': 8,
    'sept': 9, 'oct': 10, 'nov': 11, 'déc': 12
}

def fetch_data(soup) :
    lignes_joueurs = soup.find_all('tr', class_=['liste_clair', 'liste_fonce'])
    donnees_joueurs = []

    titres_colonnes = [
        "NrFFE", "NomComplet", "Af.", "Info",
        "Elo", "Rapide", "Blitz", "Cat", "M.", "Club"
    ]

    for ligne in lignes_joueurs :
        cellules = ligne.find_all('td', recursive=False)
        if len(cellules) >= len(titres_colonnes) :
            joueur_data = {}
            for i, titre in enumerate(titres_colonnes) :
                texte_cellule = cellules[i].get_text(strip=True).replace('\xa0', ' ')
                joueur_data[titre] = texte_cellule
            joueur_data["Nom"] = "".join(joueur_data["NomComplet"].split(' ')[:-1])
            joueur_data["Prénom"] = joueur_data["NomComplet"].split(' ')[-1]
            donnees_joueurs.append(joueur_data)

            lien = soup.find('a', class_="lien_texte")
            reponse_fiche = requests.get(lien)
            reponse_fiche.raise_for_status() 
            soup_fiche = BeautifulSoup(reponse_fiche.text, 'html.parser')
            joueur_data["FicheFIDE"] = soup.find('a', class_="lien_texte")
            
    return donnees_joueurs


def get_players(url) :
    all_players_data = []
    with requests.Session() as session :
        response = session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        viewstate = soup.find('input', {'__VIEWSTATE'})
        viewstategenerator = soup.find('input', {'__VIEWSTATEGENERATOR'})
        eventvalidation = soup.find('input', {'__EVENTVALIDATION'})
        
        current_payload = {
            '__VIEWSTATE' : viewstate['value'] if viewstate else '',
            '__VIEWSTATEGENERATOR' : viewstategenerator['value'] if viewstategenerator else PAYLOAD_CONSTANTES['__VIEWSTATEGENERATOR'],
            '__EVENTTARGET' : PAYLOAD_CONSTANTES['__EVENTTARGET'],
        }
        
        if eventvalidation :
            current_payload['__EVENTVALIDATION'] = eventvalidation['value']

        donnees_page_1 = fetch_data(soup)
        all_players_data.extend(donnees_page_1)

        page_num = 2
        
        while True :
            post_data = current_payload.copy()
            post_data['__EVENTARGUMENT'] = str(page_num) 

            response = session.post(url, data=post_data)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            nouvelles_donnees = fetch_data(soup)

            if nouvelles_donnees :
                all_players_data.extend(nouvelles_donnees)

                viewstate = soup.find('input', {'__VIEWSTATE'})
                if viewstate :
                    current_payload['__VIEWSTATE'] = viewstate['value']

                page_num += 1
            else :
                break
                
    return all_players_data

def get_tournaments():
    response = requests.get(URL_FFE)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    tournois_futurs = []
    today = datetime.date.today()
    current_year = None
    
    main_table = soup.find('table', attrs={'border': '0', 'cellspacing': '0', 'cellpadding': '4', 'width': '100%'})
    if not main_table:
        return []

    for row in main_table.find_all('tr', recursive=False):
        if 'RowRupture' in row.get('id', ''):
            rupture_td = row.find('td', class_='liste_titre')
            if rupture_td:
                match = re.search(r'\d{4}', rupture_td.text)
                if match:
                    current_year = int(match.group(0))
            continue
            
        if row.get('class') and (row.get('class')[0] == 'liste_fonce' or row.get('class')[0] == 'liste_clair'):
            
            if current_year is None:
                continue

            tds = row.find_all('td')
            if len(tds) >= 5:
                raw_date_str = tds[4].text.strip()

                try:
                    date_parts = raw_date_str.strip('.').split()
                    
                    if len(date_parts) == 2:
                        day_str, month_abbr = date_parts
                        month_abbr_cleaned = month_abbr.lower().replace('.', '')

                        if month_abbr_cleaned in ABBR_MONTH_MAP:
                            month = ABBR_MONTH_MAP[month_abbr_cleaned]
                            
                            tournament_date = datetime.date(current_year, month, int(day_str))

                            if tournament_date >= today:
                                ref = tds[0].text.strip()
                                ville = tds[1].text.strip()
                                departement = tds[2].text.strip()
                                
                                element_tournoi = tds[3].find('a')
                                nom = element_tournoi.text.strip() if element_tournoi else "Nom non trouvé"
                                lien = BASE_URL + element_tournoi['href'] if element_tournoi and 'href' in element_tournoi.attrs else ""
                                
                                tournois_futurs.append({
                                    "Reference": ref, "Ville": ville, "Département": departement,
                                    "NomTournoi": nom, "Date": tournament_date.strftime("%d/%m/%Y"),
                                    "LienFiche": lien
                                })

                except ValueError:
                    continue

    return tournois_futurs

def fetch_players() :
    players = get_players(URL_CLUB)
    players_sorted = sorted(
        players,
        key = itemgetter("Elo"),
        reverse = True
    )
    players_indexes = {}
    for index, player in enumerate(players_sorted) :
        players_indexes[player["NomComplet"]] = index
    with open("joueurs.json", 'w', encoding='utf-8') as file :
        json.dump(players_sorted, file, indent=4, ensure_ascii=False)
    with open("index_joueurs.json", 'w', encoding='utf-8') as file :
        json.dump(players_indexes, file, indent=4, ensure_ascii=False)

def fetch_tournaments() :
    tournaments = get_tournaments()
    with open("tournois.json", 'w', encoding='utf-8') as file :
        json.dump(tournaments, file, indent=4, ensure_ascii=False)

def search_player(nom, prénom) :
    url = "https://www.echecs.asso.fr/ListeJoueurs.aspx?Action=FFE"

    payload = {
        "Action": "FFE",
        "JoueurNom": nom
    }

    response = requests.post(url, data=payload)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    donees_joueurs = fetch_data(soup)
    
    for joueur in donees_joueurs :
        if ''.join(caractère for caractère in unidecode(joueur["Prénom"].upper()) if caractère.isalpha()) == prénom :
            return joueur

print(search_player("MAZEURE", "OSCAR"))