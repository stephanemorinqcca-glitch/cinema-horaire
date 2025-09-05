import sys
import requests
import json
from datetime import datetime, timedelta
import arrow
import os
import re

# Configuration
TOKEN = "shrfm72nvm2zmr7xpsteck6b64"
SESSION_API_URL = "https://api.useast.veezi.com/v1/session"
FILM_API_URL = "https://api.useast.veezi.com/v4/film/"
ATTRIBUTE_API_URL = "https://api.useast.veezi.com/v1/attribute/"

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

# 🔍 Récupère les détails d’un attribut
def fetch_attribute_details(attr_id, cache):
    if attr_id in cache:
        return cache[attr_id]

    url = f"{ATTRIBUTE_API_URL}{attr_id}"
    headers = {
        "VeeziAccessToken": TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Erreur HTTP {resp.status_code} pour l'attribut {attr_id}")
            return {}
        data = resp.json()
        cache[attr_id] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau pour l'attribut {attr_id} : {e}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Erreur : Réponse non JSON pour l'attribut {attr_id}")
        return {}

# 📅 Récupère toutes les séances
def fetch_sessions():
    headers = {
        "VeeziAccessToken": TOKEN,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(SESSION_API_URL, headers=headers, timeout=10)
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
    attribute_cache = {}
    used_attributes = {}
    ignored_count = 0

    now = arrow.now('America/Toronto')
    threshold = now.shift(minutes=+5)  # seuil = maintenant + 5 min

    for session in sessions:
        showtime_str = session.get("FeatureStartTime", "")
        sales_via = session.get("SalesVia", [])
        status = session.get("Status", "")

        try:
            # Pas de replace(tzinfo='UTC') si l'heure est déjà locale
            session_time = arrow.get(showtime_str, tzinfo='America/Toronto')
        except Exception as e:
            print(f"Erreur parsing heure: {showtime_str} → {e}")
            ignored_count += 1
            continue

        # Filtrage : WWW, statut ouvert, séance plus tard que maintenant + 5 min
        if "WWW" not in sales_via or status != "Open" or session_time <= threshold:
            ignored_count += 1
            continue

        # Ici, la session est valide : tu peux continuer le traitement
    
        showtime = session.get("FeatureStartTime")
        if not showtime or not isinstance(showtime, str) or showtime.strip() == "":
            ignored_count += 1
            continue

        film_id = session.get("FilmId")
        title = session.get("Title")
        rating = session.get("Rating", "")
        duration = session.get("Duration", "")
        genres = session.get("Genres", [])
        poster = session.get("FilmImageUrl", "")
        posterthumbnail = session.get("FilmPosterThumbnailUrl", "")
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
                "thumbnail": film_details.get("FilmPosterThumbnailUrl", posterthumbnail),
                "banniere": film_details.get("BackdropImageUrl", ""),
                "bande_annonce": film_details.get("FilmTrailerUrl", ""),
                "content": film_details.get("Content", ""),
                "horaire": []
            }

        enriched_attributes = [fetch_attribute_details(attr_id, attribute_cache) for attr_id in attributes]

        # Enregistrer les attributs pour la légende
        for attr in enriched_attributes:
            if attr and "Id" in attr:
                used_attributes[attr["Id"]] = {
                    "ShortName": attr.get("ShortName", ""),
                    "Description": attr.get("Description", ""),
                    "FontColor": attr.get("FontColor", "#000000"),
                    "BackgroundColor": attr.get("BackgroundColor", "#ffffff")
                }

        # Fusionner les shortnames avec espaces
        shortnames = " ".join([" " + attr.get("ShortName", "") + " " for attr in enriched_attributes if attr])
        films_dict[film_id]["horaire"].append({
            "horaire": showtime_str + " " + shortnames.strip()
        })

    print(f"⚠️ Séances ignorées : {ignored_count}")
    
    for film in films_dict.values():
        # film["horaire"].sort(key=lambda h: h["horaire"])

        def extract_datetime_safe(horaire_str):
            # Cherche une date/heure au début de la chaîne
            match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", horaire_str)
            if match:
                return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
            else:
                # Si la date est introuvable, on met une date très éloignée pour la placer en dernier
                return datetime.max

        # Appliquer le tri à tous les films
        for film in films_dict.values():
            film["horaire"].sort(key=lambda h: extract_datetime_safe(h["horaire"]))

        films_list = list(films_dict.values())
        films_list.sort(key=lambda film: film["titre"].lower())

        legend_list = list(used_attributes.values())
        legend_list.sort(key=lambda attr: attr["ShortName"].lower())

        return {
            "cinema": "Cinéma Centre-Ville",
            "legende": legend_list,
            "films": films_list
        }

# 🚀 Point d’entrée
def main():
    sessions = fetch_sessions()
    if not sessions:
        print("❌ Aucune séance récupérée.")
        sys.exit(1)
        
    data = transform_data(sessions)   
    final_file = "films.json"

    # Génère le nouveau contenu JSON sous forme de chaîne
    new_content = json.dumps(data, ensure_ascii=False, indent=2)

    try
        # Vérifie si le fichier existe et si le contenu est identique    
        if os.path.exists(final_file):
            with open(final_file, "r", encoding="utf-8") as f:
                existing_content = f.read()
        if existing_content == new_content:
            print("ℹ️ Aucun changement détecté dans films.json.")
            return

        # Écrit uniquement si le contenu est différent ou si le fichier n'existe pas
        with open(final_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("✅ Fichier films.json mis à jour.")
        print(f"Nombre de films ajoutés : {len(data['films'])}")
        
    except IOError as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

