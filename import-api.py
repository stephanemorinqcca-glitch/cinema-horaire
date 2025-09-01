#!/usr/bin/env python3
# import-api.py

import requests
import json
import sys
from datetime import datetime, timedelta

# 1. Configuration
TOKEN = "shrfm72nvm2zmr7xpsteck6b64"
API_URL = "https://api.us.veezi.com/v1/sessions"

# Arguments optionnels : dates de début et fin
start_date = sys.argv[1] if len(sys.argv) > 1 else datetime.today().strftime("%Y-%m-%d")
end_date = sys.argv[2] if len(sys.argv) > 2 else (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")

# 2. Récupération des séances
params = {
    "startDate": start_date,
    "endDate": end_date,
    "cinemaId": "0",
    "includeFilms": "true"
}
headers = {"VeeziAccessToken": TOKEN}

resp = requests.get(API_URL, params=params, headers=headers)
resp.raise_for_status()
sessions = resp.json()

# 3. Transformation des données
films_map = {}
for s in sessions:
    fid = s["filmId"]
    # Initialisation du film
    if fid not in films_map:
        films_map[fid] = {
            "titre":          s["filmTitle"],
            "classification": s["rating"],
            "duree":          s["duration"],
            "genre":          s["genres"],
            "poster":         s.get("filmImageUrl"),
            "horaire":        []
        }
    # Ajout de l’horaire formaté
    dt = datetime.fromisoformat(s["showtime"])
    films_map[fid]["horaire"].append(dt.strftime("%d/%m/%Y %H:%M"))

# Trie des horaires et mise en forme finale
output = {
    "cinema": "Cinéma Centre-Ville",
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "films": [
        { **film, "horaire": sorted(film["horaire"]) }
        for film in films_map.values()
    ]
}

# 4. Écriture dans films.json
with open("films.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ films.json généré ({len(output['films'])} films, plages {start_date} → {end_date})")
