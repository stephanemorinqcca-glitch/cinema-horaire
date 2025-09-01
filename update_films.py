import subprocess
import sys

import os
TOKEN = os.getenv("VEEZI_ACCESS_TOKEN")
if not TOKEN:
    raise RuntimeError("Il manque la variable d'environnement VEEZI_ACCESS_TOKEN")

# Installer les dépendances automatiquement
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

import requests
import json
from datetime import date
import arrow
import os

# 1. Corrige l'endpoint selon ta région Veezi
#    - US East    : https://api.useast.veezi.com/sessions
#    - Europe     : https://api.eu.veezi.com/v1/sessions
#    - US West    : https://api.uswest.veezi.com/v1/sessions
API_URL = os.getenv("VEEZI_API_URL",
    "https://api.useast.veezi.com/v1/sessions"
)

def fetch_sessions():
    headers = {
        "VeeziAccessToken": TOKEN
    }
    params = {
        "startDate":    date.today().isoformat(),
        "endDate":      "2100-01-01",
        "includeFilms": "true",
        "pageSize":     500,
        "pageNumber":   1
    }

    all_sessions = []
    while True:
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
            print("→ URL appelée :", resp.request.url)
            print("→ En-têtes envoyés :", resp.request.headers)
            print("→ Code reçu :", resp.status_code)
            print("→ Content-Type :", resp.headers.get("content-type"))
            print("→ Corps brut :", resp.text[:200], "…")
            resp.raise_for_status()
            data = resp.json()
            print(resp.json())
        except requests.HTTPError as http_err:
            print(f"Erreur HTTP : {http_err} → {resp.url}")
            break
        except requests.RequestException as req_err:
            print(f"Erreur réseau : {req_err}")
            break

        print(f"→ GET {resp.url} | status {resp.status_code}")

        # On s’assure d’un JSON en retour
        if "application/json" not in resp.headers.get("Content-Type", ""):
            print("Réponse non JSON, contenu partiel :\n", resp.text[:200])
            break

        page_data = resp.json()
        count = len(page_data) if isinstance(page_data, list) else 0
        print(f"→ page {params['pageNumber']}: {count} séances récupérées")

        if not page_data:
            break

        all_sessions.extend(page_data)
        params["pageNumber"] += 1

    print(f"Total séances récupérées : {len(all_sessions)}")
    return all_sessions

def transform_data(sessions):
    films = {}
    for sess in sessions:
        fid     = sess.get("filmId")
        title   = sess.get("filmTitle")
        iso     = sess.get("showtime")
        rating  = sess.get("rating", "")
        duration= sess.get("duration", "")
        genres  = sess.get("genres", [])
        poster  = sess.get("filmImageUrl", "")

        try:
            dt = arrow.get(iso)
            horaire = dt.format("YYYY-MM-DD HH:mm")
        except Exception as e:
            print(f"Parse error pour '{iso}': {e}")
            continue

        if fid not in films:
            films[fid] = {
                "titre":          title,
                "horaire":        [],
                "classification": rating,
                "duree":          duration,
                "genre":          genres,
                "poster":         poster
            }
        films[fid]["horaire"].append(horaire)

    for film in films.values():
        film["horaire"].sort()
    return {
        "cinema": "Cinéma Centre-Ville",
        "films":  list(films.values())
    }

def main():
    sessions = fetch_sessions()
    data     = transform_data(sessions)

    with open("films1.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("films1.json mis à jour !")

if __name__ == "__main__":
    main()
