import subprocess
import sys
import os
import requests
import json
from datetime import date
import arrow

# Installer les dépendances automatiquement
subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

# Configuration
TOKEN = os.getenv("VEEZI_ACCESS_TOKEN")
API_URL = os.getenv("VEEZI_API_URL", "https://api.useast.veezi.com/api/v1/sessions")
FILM_API = "https://api.us.veezi.com/v4/film/"

if not TOKEN:
    raise RuntimeError("Il manque la variable d'environnement VEEZI_ACCESS_TOKEN")

# 🔍 Récupère les détails d’un film
def fetch_film_details(fid):
    url = f"{FILM_API}{fid}"
    headers = {"VeeziAccessToken": TOKEN}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Erreur pour le film {fid}: {e}")
        return {}

# 📅 Récupère toutes les séances
def fetch_sessions():
    headers = {"VeeziAccessToken": TOKEN}
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
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"Erreur réseau : {e}")
            break
        if not data:
            break
        all_sessions.extend(data)
        params["pageNumber"] += 1
    return all_sessions

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films = {}
    for sess in sessions:
        fid      = sess.get("filmId")
        title    = sess.get("filmTitle")
        iso      = sess.get("showtime")
        rating   = sess.get("rating", "")
        duration = sess.get("duration", "")
        genres   = sess.get("genres", [])
        poster   = sess.get("filmImageUrl", "")
        attrs    = sess.get("attributes", [])

        try:
            dt = arrow.get(iso)
            horaire = dt.format("YYYY-MM-DD HH:mm")
        except Exception as e:
            print(f"Parse error pour '{iso}': {e}")
            continue

        if fid not in films:
            film_details = fetch_film_details(fid)
            films[fid] = {
                "id": fid,
                "titre": film_details.get("Title", title),
                "synopsis": film_details.get("Synopsis", ""),
                "classification": film_details.get("Rating", rating),
                "duree": film_details.get("Duration", duration),
                "genre": film_details.get("Genre", genres),
                "format": film_details.get("PresentationType", ""),
                "langue": film_details.get("AudioLanguage", ""),
                "distributeur": film_details.get("Distributor", ""),
                "realisateur": next((p["FirstName"] + " " + p["LastName"] for p in film_details.get("People", []) if p["Role"] == "Director"), ""),
                "acteurs": [p["FirstName"] + " " + p["LastName"] for p in film_details.get("People", []) if p["Role"] == "Actor"],
                "affiche": film_details.get("FilmPosterUrl", poster),
                "banniere": film_details.get("BackdropImageUrl", ""),
                "bande_annonce": film_details.get("FilmTrailerUrl", ""),
                "seances": []
            }

        films[fid]["seances"].append({
            "horaire": horaire,
            "attributs": attrs
        })

    return {
        "cinema": "Cinéma Centre-Ville",
        "films": list(films.values())
    }

# 🔎 Filtre les films par date et format
def filtrer_films(data, date_cible=None, format_cible=None):
    resultat = []
    for film in data["films"]:
        seances_filtrees = []
        for seance in film["seances"]:
            if date_cible and not seance["horaire"].startswith(date_cible):
                continue
            if format_cible and format_cible not in seance.get("attributs", []):
                continue
            seances_filtrees.append(seance)
        if seances_filtrees:
            film_filtre = film.copy()
            film_filtre["seances"] = seances_filtrees
            resultat.append(film_filtre)
    return {"cinema": data["cinema"], "films": resultat}

# 🚀 Point d’entrée
def main():
    sessions = fetch_sessions()
    data = transform_data(sessions)
    with open("films1.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("films1.json mis à jour !")

if __name__ == "__main__":
    main()
