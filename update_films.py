import requests
import json
from datetime import datetime

API_URL = "https://ticketing.useast.veezi.com/sessions/?siteToken=jjwk2hm92x8zmdt4ys4sr1vvp0"

def fetch_sessions():
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erreur lors de la récupération des données : {response.status_code}")
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

        if film_id not in films_dict:
            films_dict[film_id] = {
                "titre": title,
                "horaire": [],
                "classification": classification,
                "duree": duration,
                "genre": genres,
                "poster": poster
            }

        films_dict[film_id]["horaire"].append(showtime)

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
