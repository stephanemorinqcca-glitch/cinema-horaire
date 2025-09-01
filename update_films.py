import subprocess
import sys

# Installer les dépendances automatiquement
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

import requests
import json
from datetime import date
import arrow

API_URL    = "https://api.us.veezi.com/v1/sessions"
SITE_TOKEN = "shrfm72nvm2zmr7xpsteck6b64"

def fetch_sessions():
    headers = {
        "VeeziAccessToken": SITE_TOKEN
    }
    # Pagination : pageSize maximale et numéro de page
    params = {
        "startDate":  date.today().isoformat(),
        "endDate":    "2100-01-01",
        "includeFilms": "true",
        "pageSize":   500,
        "pageNumber": 1
    }

    all_sessions = []
    while True:
        try:
            resp = requests.get(API_URL, headers=headers, params=params)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Erreur réseau / HTTP : {e}")
            break

        # DEBUG → URL complète et code HTTP
        print(f"→ GET {resp.url} | status {resp.status_code}")

        # Parser le JSON et debugger
        if "application/json" in resp.headers.get("Content-Type", ""):
            page_data = resp.json()
            count = len(page_data) if isinstance(page_data, list) else 0
            print(f"→ page {params['pageNumber']} : {count} séances récupérées")
        else:
            print("La réponse n'est pas en JSON. Contenu reçu :")
            print(resp.text[:500])
            break

        # Si plus de données, on les accumule, sinon on sort
        if not page_data:
            break

        all_sessions.extend(page_data)
        params["pageNumber"] += 1

    print(f"Total séances récupérées : {len(all_sessions)}")
    return all_sessions

def transform_data(sessions):
    films_dict = {}

    for session in sessions:
        film_id      = session.get("filmId")
        title        = session.get("filmTitle")
        showtime_iso = session.get("showtime")
        classification = session.get("rating", "")
        duration     = session.get("duration", "")
        genres       = session.get("genres", [])
        poster       = session.get("filmImageUrl", "")

        try:
            dt = arrow.get(showtime_iso)
            showtime_str = dt.format("YYYY-MM-DD HH:mm")
        except Exception as e:
            print(f"Erreur de parsing pour {showtime_iso} → {e}")
            continue

        if film_id not in films_dict:
            films_dict[film_id] = {
                "titre":         title,
                "horaire":       [],
                "classification": classification,
                "duree":         duration,
                "genre":         genres,
                "poster":        poster
            }

        films_dict[film_id]["horaire"].append(showtime_str)

    # Trier les horaires par film
    for film in films_dict.values():
        film["horaire"].sort()

    return {
        "cinema": "Cinéma Centre-Ville",
        "films":  list(films_dict.values())
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
