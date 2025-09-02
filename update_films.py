import subprocess
import sys
import os
import requests
import json
from datetime import date
import arrow

# Installer les dépendances automatiquement (à commenter si déjà installées)
# subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# Configuration
TOKEN = os.getenv("VEEZI_ACCESS_TOKEN")
API_URL = os.getenv("VEEZI_API_URL", "https://api.useast.veezi.com/api/v1/sessions")
FILM_API = "https://api.us.veezi.com/v4/film/"

if not TOKEN:
    print("❌ Erreur : Le token Veezi n'est pas défini dans les variables d'environnement (VEEZI_ACCESS_TOKEN).")
    sys.exit(1)

# 🔍 Récupère les détails d’un film
def fetch_film_details(fid):
    url = f"{FILM_API}{fid}"
    headers = {
        "VeeziAccessToken": TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Erreur HTTP {resp.status_code} pour le film {fid}")
            return {}
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau pour le film {fid} : {e}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Erreur : Réponse non JSON pour le film {fid}")
        return {}

# 📅 Récupère toutes les séances
def fetch_sessions():
    headers = {
        "VeeziAccessToken": TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    params = {
        "startDate": date.today().isoformat(),
        "endDate": "2100-01-01",
        "includeFilms": "true",
        "pageSize": 500,
        "pageNumber": 1
    }
    all_sessions = []
    while True:
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"❌ Erreur HTTP {resp.status_code} lors de la récupération des séances.")
                break
            try:
                data = resp.json()
            except json.JSONDecodeError:
                print("❌ Erreur : La réponse des séances n'est pas au format JSON.")
                break
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur réseau : {e}")
            break
        if not data:
            break
        all_sessions.extend(data)
        params["pageNumber"] += 1
    return all_sessions

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films_dict = {}
    for session in sessions:
        film_id = session.get("filmId")
        title = session.get("filmTitle")
        showtime = session.get("showtime")
        rating = session.get("rating", "")
        duration = session.get("duration", "")
        genres = session.get("genres", [])
        poster = session.get("filmImageUrl", "")
        attributes = session.get("attributes", [])

        try:
            dt = arrow.get(showtime)
            showtime_str = dt.format("YYYY-MM-DD HH:mm")
        except Exception as e:
            print(f"Erreur de format de date pour {showtime}: {e}")
            continue

        if film_id not in films_dict:
            film_details = fetch_film_details(film_id)
            films_dict[film_id] = {
                "id": film_id,
                "titre": film_details.get("Title", title),
                "synopsis": film_details.get("Synopsis", ""),
                "classification": film_details.get("Rating", rating),
                "duree": film_details.get("Duration", duration),
                "genre": film_details.get("Genre", genres),
                "format": film_details.get("PresentationType", ""),
                "affiche": film_details.get("FilmPosterUrl", poster),
                "banniere": film_details.get("BackdropImageUrl", ""),
                "bande_annonce": film_details.get("FilmTrailerUrl", ""),
                "horaire": []
            }

        films_dict[film_id]["horaire"].append({
            "horaire": showtime_str,
            "attributs": attributes
        })

    # Tri des horaires
    for film in films_dict.values():
        film["horaire"].sort(key=lambda h: h["horaire"])

    return {
        "cinema": "Cinéma Centre-Ville",
        "films": list(films_dict.values())
    }

# 🚀 Point d’entrée
def main():
    sessions = fetch_sessions()
    if not sessions:
        print("❌ Aucune séance récupérée.")
        sys.exit(1)
    data = transform_data(sessions)
    try:
        with open("films1.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ Fichier films1.json mis à jour avec attributs de séance.")
    except IOError as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
