import requests
import json
from datetime import datetime
from dateutil.parser import parse

API_URL = "https://api.us.veezi.com"
SITE_TOKEN = "jjwk2hm92x8zmdt4ys4sr1vvp0"

def fetch_sessions():
    headers = {
        "VeeziAccessToken": SITE_TOKEN
    }

    try:
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()

        if "application/json" in response.headers.get("Content-Type", ""):
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
        film_id = session.get("filmId")
        title = session.get("filmTitle")
        showtime = session.get("showtime")
        classification = session.get("rating", "")
        duration = session.get("duration", "")
        genres = session.get("genres", [])
        poster = session.get("filmImageUrl", "")

        try:
            showtime_dt = parse(showtime)
            showtime_str = showtime_dt.strftime("%Y-%m-%d %H:%M")
        except Exception as e:
            print(f"Erreur de parsing pour l'horaire : {showtime} - {e}")
            continue

        if film_id not in films_dict:
            films_dict[film_id] = {
                "titre": title,
                "horaire": [],
                "classification": classification,
                "duree": duration,
                "genre": genres,
                "poster": poster
            }

        films_dict[film_id]["horaire"].append(showtime_str)

    for film in films_dict.values():
        film["horaire"].sort()

    return {
        "cinema": "Cinéma Centre-Ville",
        "films": list(films_dict.values())
    }

def main():
    sessions = fetch_sessions()
    data = transform_data(sessions)

    with open("films.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Fichier films.json mis à jour à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
