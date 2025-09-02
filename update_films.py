import sys
import requests
import json
from datetime import datetime
import arrow

# Configuration
TOKEN = "shrfm72nvm2zmr7xpsteck6b64"
SESSION_API_URL = "https://api.us.veezi.com/v1/session"
FILM_API_URL = "https://api.us.veezi.com/v4/film/"

# 🔍 Récupère les détails d’un film
def fetch_film_details(fid):
    url = f"{FILM_API_URL}{fid}"
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
        "startDate": datetime.today().strftime("%Y-%m-%dT00:00:00"),
        "endDate": "2110-01-01T23:59:00"
    }
    try:
        resp = requests.get(SESSION_API_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Erreur HTTP {resp.status_code} lors de la récupération des séances.")
            return []
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau : {e}")
        return []
    except json.JSONDecodeError:
        print("❌ Erreur : La réponse des séances n'est pas au format JSON.")
        return []

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films_dict = {}
    ignored_count = 0

    for session in sessions:
        sales_via = session.get("SalesVia", [])
        status = session.get("Status", "")
        if "WWW" not in sales_via or status != "Open":
            ignored_count += 1
            continue

        showtime = session.get("PreShowStartTime")
        if not showtime or not isinstance(showtime, str) or showtime.strip() == "":
            ignored_count += 1
            continue

        film_id = session.get("FilmId")
        title = session.get("Title")
        rating = session.get("Rating", "")
        duration = session.get("Duration", "")
        genres = session.get("Genres", [])
        poster = session.get("FilmImageUrl", "")
        attributes = session.get("Attributes", [])

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
                    "format": film_details.get("Format", ""),
                    "affiche": film_details.get("FilmPosterUrl", poster),
                    "banniere": film_details.get("BackdropImageUrl", ""),
                    "bande_annonce": film_details.get("FilmTrailerUrl", ""),
                    "content": film_details.get("Content", ""),
                    "horaire": []
            }

        films_dict[film_id]["horaire"].append({
            "horaire": showtime_str,
            "attributs": attributes
        })

    print(f"⚠️ Séances ignorées : {ignored_count}")

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
        with open("films.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ Fichier films.json mis à jour avec attributs de séance.")
        print(f"Nombre de films ajoutés : {len(data['films'])}")
    except IOError as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
