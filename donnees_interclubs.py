import time
import requests
from bs4 import BeautifulSoup

def extractAppState(htmlContent) :
    soupObj = BeautifulSoup(htmlContent, "html.parser")
    stateData = {}
    for fieldId in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"] :
        tagObj = soupObj.find("input", {"id" : fieldId})
        stateData[fieldId] = tagObj.get("value", "") if tagObj else None
    return stateData

def findCompetitionId(htmlContent, targetName) :
    """Parses the dropdown to find the dynamic ID for a given competition name."""
    soupObj = BeautifulSoup(htmlContent, "html.parser")
    selectElement = soupObj.find("select", {"name" : "ctl00$ContentPlaceHolderMain$SelectCompetition"})
    
    if selectElement :
        for optionTag in selectElement.find_all("option") :
            if targetName.lower() in optionTag.text.lower() :
                return optionTag.get("value")
    return None

baseUrl = "https://www.echecs.asso.fr/Equipes.aspx"
sessionObj = requests.Session()

sessionObj.headers.update({
    "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept" : "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Origin" : "https://www.echecs.asso.fr",
    "Referer" : baseUrl
})

seasonIndex = 0

while True :
    # Step 1 : Reset to base page to clearly read the next available season
    baseResponse = sessionObj.get(baseUrl)
    appState = extractAppState(baseResponse.text)
    soupObj = BeautifulSoup(baseResponse.text, "html.parser")
    
    seasonLinkId = f"ctl00_ContentPlaceHolderMain_RepeaterSaisons_ctl{seasonIndex :02d}_SaisonBase"
    seasonTarget = f"ctl00$ContentPlaceHolderMain$RepeaterSaisons$ctl{seasonIndex :02d}$SaisonBase"
    
    seasonLink = soupObj.find("a", {"id" : seasonLinkId})
    
    if not seasonLink :
        print(f"End of available seasons reached. Process completed.")
        break
        
    yearText = seasonLink.text.strip()
    print(f"\n========== Processing Season : {yearText} ==========")
    
    # Step 2 : Select the season
    payloadSeason = {
        "__EVENTTARGET" : seasonTarget,
        "__EVENTARGUMENT" : "",
        "__LASTFOCUS" : "",
        "__VIEWSTATE" : appState["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR" : appState["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION" : appState["__EVENTVALIDATION"]
    }
    
    seasonResponse = sessionObj.post(baseUrl, data = payloadSeason)
    appState = extractAppState(seasonResponse.text)
    
    # Step 3 : Dynamically find the Competition ID
    compId = findCompetitionId(seasonResponse.text, "Interclubs Adultes")
    if compId == None :
        compId = findCompetitionId(seasonResponse.text, "Interclub Adulte")
    
    if not compId :
        print(f"Competition 'Interclubs Adultes' not found for {yearText}.")
        seasonIndex += 2
        continue
        
    print(f"Found Competition ID : {compId}")
    
    # Step 4 : Select the Competition
    payloadComp = {
        "__EVENTTARGET" : "ctl00$ContentPlaceHolderMain$SelectCompetition",
        "__EVENTARGUMENT" : "",
        "__VIEWSTATE" : appState["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR" : appState["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION" : appState["__EVENTVALIDATION"],
        "ctl00$ContentPlaceHolderMain$SelectCompetition" : compId
    }
    
    compResponse = sessionObj.post(baseUrl, data = payloadComp)
    appState = extractAppState(compResponse.text)
    
    if not appState["__VIEWSTATE"] :
        print(f"State lost during competition selection for {yearText}.")
        seasonIndex += 2
        continue
        
    # Step 5 & 6 : Loop through Divisions and Groups
    for divisionId in range(7, 10) :
        payloadDiv = {
            "__EVENTTARGET" : "ctl00$ContentPlaceHolderMain$SelectDivision",
            "__EVENTARGUMENT" : "",
            "__VIEWSTATE" : appState["__VIEWSTATE"],
            "__VIEWSTATEGENERATOR" : appState["__VIEWSTATEGENERATOR"],
            "__EVENTVALIDATION" : appState["__EVENTVALIDATION"],
            "ctl00$ContentPlaceHolderMain$SelectCompetition" : compId,
            "ctl00$ContentPlaceHolderMain$SelectDivision" : str(divisionId)
        }
        
        divResponse = sessionObj.post(baseUrl, data = payloadDiv)
        divState = extractAppState(divResponse.text)

        if not divState["__VIEWSTATE"] :
            continue

        for groupId in range(0, 301) :
            payloadGroup = {
                "__EVENTTARGET" : "ctl00$ContentPlaceHolderMain$SelectGroupe",
                "__EVENTARGUMENT" : "",
                "__VIEWSTATE" : divState["__VIEWSTATE"],
                "__VIEWSTATEGENERATOR" : divState["__VIEWSTATEGENERATOR"],
                "__EVENTVALIDATION" : divState["__EVENTVALIDATION"],
                "ctl00$ContentPlaceHolderMain$SelectCompetition" : compId,
                "ctl00$ContentPlaceHolderMain$SelectDivision" : str(divisionId),
                "ctl00$ContentPlaceHolderMain$SelectGroupe" : str(groupId)
            }

            try :
                finalResponse = sessionObj.post(baseUrl, data = payloadGroup)
                if "tableau_violet" in finalResponse.text :
                    # Adding the year to the filename to avoid overwrites
                    fileName = f"saison{yearText}_div{divisionId}_grp{groupId}.html"
                    with open(fileName, "w", encoding = "utf-8") as fileObj :
                        fileObj.write(finalResponse.text)
                    print(f"Saved : Season {yearText} - Div {divisionId} - Group {groupId}")
                
                time.sleep(0.3)
            except Exception as errorMsg :
                print(f"Error : {errorMsg}")

    # Move to the next season
    seasonIndex += 2