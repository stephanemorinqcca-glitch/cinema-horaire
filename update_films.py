import sys
import requests
import json
from datetime import datetime, timedelta
import os
import re
import hashlib
import pytz
from typing import Optional

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

def extract_datetime_safe(horaire_str):
    match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", horaire_str)
    if match:
        naive_dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M")
        tz = pytz.timezone('America/Toronto')
        return tz.localize(naive_dt)
    else:
        return datetime.max.replace(tzinfo=pytz.UTC)

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films_dict = {}
    attribute_cache = {}
    used_attributes = {}
    ignored_count = 0

    # Fuseau horaire
    tz = pytz.timezone('America/Toronto')
    now = datetime.now(tz)
    threshold = now + timedelta(minutes=0)

    for session in sessions:
        showtime_str = session.get("FeatureStartTime", "")
        sales_via = session.get("SalesVia", [])
        status = session.get("Status", "")

        # Dans la boucle des sessions
        try:
            session_time = datetime.strptime(showtime_str, "%Y-%m-%dT%H:%M:%S")
            session_time = tz.localize(session_time)
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

        # Format d'affichage
        try:
            dt = datetime.strptime(showtime, "%Y-%m-%dT%H:%M:%S")
            showtime_str = dt.strftime("%Y-%m-%d %H:%M")
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
        film["horaire"].sort(key=lambda h: extract_datetime_safe(h["horaire"]))

        # Ajouter le timestamp de la dernière séance (date + heure) dans films_dict[film_id]
        horaires_valides = [extract_datetime_safe(h["horaire"]) for h in film["horaire"]]
        if horaires_valides:
            derniere_seance = max(horaires_valides)
            film["last_show"] = int(derniere_seance.timestamp())
        else:
            film["last_show"] = None

    films_list = list(films_dict.values())
    films_list.sort(key=lambda film: film["titre"].lower())

    legend_list = list(used_attributes.values())
    legend_list.sort(key=lambda attr: attr["ShortName"].lower())

    for film in films_list:
        print(f"{film['titre']} → last_show: {film['last_show']}")

    return {
        "cinema": "Cinéma Centre-Ville",
        "legende": legend_list,
        "films": films_list
    }

def compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def load_previous_checksum(file_path: str) -> Optional[str]:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("checksum")
    except Exception as e:
        print(f"⚠️ Erreur lecture checksum : {e}")
        return None

def save_checksum(file_path: str, checksum: str):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"checksum": checksum}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Erreur écriture checksum : {e}")

# 🚀 Point d’entrée
def main():
    sessions = fetch_sessions()
    if not sessions:
        print("❌ Aucune séance récupérée.")
        sys.exit(1)

    data = transform_data(sessions)
    final_file = "films.json"
    temp_file = "films_temp.json"
    checksum_file = "checksumfilms.json"

    # Génère le nouveau contenu JSON sous forme de chaîne
    new_content = json.dumps(data, ensure_ascii=False, indent=2)
    new_checksum = compute_checksum(new_content)
    old_checksum = load_previous_checksum(checksum_file)
    if old_checksum is None:
        print("📁 Aucun fichier de checksum trouvé. Création de checksumfilms.json et films.json.")

    try:
        if new_checksum == old_checksum and os.path.exists(final_file):
            print("ℹ️ Aucun changement détecté (checksum identique).")
            return

        # Création ou mise à jour du fichier
        if not os.path.exists(final_file):
            print("📁 Fichier films.json absent. Création forcée.")

        print("🔄 Changement détecté ou fichier manquant. Mise à jour de films.json.")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(temp_file, final_file)
        save_checksum(checksum_file, new_checksum)
        print(f"✅ Fichier films.json mis à jour avec {len(data['films'])} films.")
    
    except IOError as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
