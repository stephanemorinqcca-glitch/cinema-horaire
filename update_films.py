import subprocess
import sys

# Installer les dépendances automatiquement
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

import requests
import json
from datetime import datetime, date
import arrow

API_URL = "https://api.useast.veezi.com/v1/sessions"
SITE_TOKEN = "shrfm72nvm2zmr7xpsteck6b64"

def fetch_sessions():
    headers = {
        "VeeziAccessToken": SITE_TOKEN
    }
    params = {
        "startDate": date.today().isoformat(),
        "endDate": "2100-01-01",
        "includeFilms": "true"
    }
    try:
        response = requests.get(API_URL, headers=headers, params=params)
        response.raise_for_status()
        # DEBUG → affiche l’URL complète et le code HTTP
        print(f"→ GET {response.url}  | status {response.status_code}")
        if "application/json" in response.headers.get("Content-Type", ""):
            # DEBUG → nombre d'éléments renvoyés
           print("→ JSON récupéré:", 
           isinstance(data, list) and f"{len(data)} sessions" or type(data))
           return response.json()
        else:
            print("La réponse n'est pas en JSON. Contenu reçu :")
            print(response.text[:500])
            return []
    except requests.RequestException as e:
        print(f"Erreur réseau : {e}")
        return []

def transform_data(sessions):
    films_dict = {}
    for session in sessions:
        film_id       = session.get("filmId")
        title         = session.get("filmTitle")
        showtime_iso  = session.get("showtime")
        classification= session.get("rating", "")
        duration      = session.get("duration", "")
        genres        = session.get("genres", [])
        poster        = session.get("filmImageUrl", "")

        try:
            # arrow gère le parsing ISO 8601 et les fuseaux
            showtime_dt  = arrow.get(showtime_iso)
            # format YYYY-MM-DD HH:mm
            showtime_str = showtime_dt.format("YYYY-MM-DD HH:mm")
        except Exception as e:
            print(f"Erreur de parsing pour l'horaire : {showtime_iso} - {e}")
            continue

        if film_id not in films_dict:
            films_dict[film_id] = {
                "titre"         : title,
                "horaire"       : [],
                "classification": classification,
                "duree"         : duration,
                "genre"         : genres,
                "poster"        : poster
            }
        films_dict[film_id]["horaire"].append(showtime_str)

    # Trier les horaires pour chaque film
    for film in films_dict.values():
        film["horaire"].sort()

    return {
        "cinema": "Cinéma Centre-Ville",
        "films" : list(films_dict.values())
    }

def main():
    sessions = fetch_sessions()
    data     = transform_data(sessions)
    with open("films1.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    now_str = arrow.now().format("YYYY-MM-DD HH:mm:ss")
    print(f"Fichier films1.json mis à jour à {now_str}")

if __name__ == "__main__":
    main()
