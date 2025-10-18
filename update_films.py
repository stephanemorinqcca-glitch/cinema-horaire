import sys
import requests
import json
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import os
import re
import hashlib
import pytz
from typing import Optional

# 🔑 Configuration
TOKEN = "shrfm72nvm2zmr7xpsteck6b64"
SESSION_API_URL = "https://api.useast.veezi.com/v1/session"
FILM_API_URL = "https://api.useast.veezi.com/v4/film/"
ATTRIBUTE_API_URL = "https://api.useast.veezi.com/v1/attribute/"
HEADERS = {
    "VeeziAccessToken": TOKEN,
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# 🌐 Fonction générique JSON
def fetch_json(url: str, headers: dict, cache: dict = None, key: str = None):
    """Récupère du JSON depuis une URL avec gestion d'erreurs et cache optionnel."""
    if cache is not None and key in cache:
        return cache[key]
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if cache is not None and key is not None:
            cache[key] = data
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau ou HTTP pour {url} : {e}")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Erreur : Réponse non JSON pour {url}")
        return {}

# 🎬 Détails d’un film
def fetch_film_details(fid: str):
    url = f"{FILM_API_URL}{fid}"
    return fetch_json(url, headers=HEADERS)

# 🏷️ Détails d’un attribut (avec cache)
def fetch_attribute_details(aid: str, cache: dict):
    url = f"{ATTRIBUTE_API_URL}{aid}"
    return fetch_json(url, headers=HEADERS, cache=cache, key=aid)

# 📅 Liste des séances
def fetch_sessions():
    return fetch_json(SESSION_API_URL, headers=HEADERS) or []

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films_dict = {}
    attribute_cache = {}
    used_attributes = {}
    ignored_count = 0

    tz = pytz.timezone('America/Toronto')
    now = datetime.now(tz)
    threshold = now + timedelta(minutes=0)

    for session in sessions:
        session_id = session.get("Id")
        showtime_str = session.get("FeatureStartTime", "")
        sales_via = session.get("SalesVia", [])
        status = session.get("Status", "")
        tickets_sold_out = session.get("TicketsSoldOut", False)
        show_type = session.get("ShowType", "")
        seats_available = session.get("SeatsAvailable", None)
        
        try:
            session_time = datetime.strptime(showtime_str, "%Y-%m-%dT%H:%M:%S")
            session_time = tz.localize(session_time)
        except Exception as e:
            print(f"Erreur parsing heure: {showtime_str} → {e}")
            ignored_count += 1
            continue
        
        # print("🕒 Session:", session_time.strftime("%d/%m/%Y %H:%M"))
        # print("    Threshold:", threshold.strftime("%d/%m/%Y %H:%M"))
        # print("    session_time < threshold:", session_time < threshold)

        # 👇 Est-ce que l'on garde la session
        if (
            "WWW" not in sales_via
            or status != "Open"
            or show_type != "Public"
            or session_time <= threshold
        ):
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
            dt = datetime.strptime(showtime_str, "%Y-%m-%dT%H:%M:%S")
            jour = dt.strftime("%Y-%m-%d")
            heure = dt.strftime("%H:%M")
        except Exception as e:
            print(f"Erreur de format de date pour {showtime_str}: {e}")
            continue

        if film_id not in films_dict:
            film_details = fetch_film_details(film_id)

            # Récupération et formatage de la date d'ouverture
            raw_date_opening = film_details.get("OpeningDate", "")
            opening_date = raw_date_opening.split("T")[0] if "T" in raw_date_opening else raw_date_opening
            
            films_dict[film_id] = {
                "id": film_id,
                "titre": film_details.get("Title", title),
                "OpeningDate": opening_date,
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
                "horaire": {}
            }

        enriched_attributes = [fetch_attribute_details(attr_id, attribute_cache) for attr_id in attributes]

        for attr in enriched_attributes:
            if attr and "Id" in attr:
                used_attributes[attr["Id"]] = {
                    "ShortName": attr.get("ShortName", ""),
                    "Description": attr.get("Description", ""),
                    "FontColor": attr.get("FontColor", "#000000"),
                    "BackgroundColor": attr.get("BackgroundColor", "#ffffff"),
                    "ShowOnSessionsWithNoComps": attr.get("ShowOnSessionsWithNoComps", False)
                }

        attributs = [attr.get("ShortName", "").strip() for attr in enriched_attributes if attr]
        attributs = sorted([a for a in attributs if a], key=str.lower)

        # Injecter "3D" si le format du film est "3D Digital"
        if films_dict[film_id].get("format", "").strip().lower() == "3d digital":
            if "3D" not in attributs:
                attributs.insert(0, "3D")
                
        # if tickets_sold_out:
        #    attributs.insert(0, "COMPLET")

        # Ajout de l'attribut "COMPLET" si moins de 11 places disponibles
        # print(f"🎟️ Places disponibles pour la session {session_id} : {seats_available}")
        if tickets_sold_out or (seats_available and seats_available < 11):
            attributs.insert(0, "COMPLET")
        
        films_dict[film_id]["horaire"].setdefault(jour, []).append({
            "session_id": session_id,
            "heure": heure,
            "attributs": attributs,
            "placesDisponibles": seats_available
        })

    # Tri des films à l'affiche par jours/heures
    for film in films_dict.values():
        # Tri des jours (dates)
        film["horaire"] = dict(sorted(film["horaire"].items(), key=lambda x: x[0]))

        # Tri des séances par heure pour chaque jour
        for jour in film["horaire"]:
            film["horaire"][jour].sort(key=lambda s: s["heure"])

        # Calcul de la première et dernière séance
        toutes_les_dates = []
        for jour, seances in film["horaire"].items():
            for s in seances:
                dt = datetime.strptime(f"{jour} {s['heure']}", "%Y-%m-%d %H:%M")
                tz = pytz.timezone('America/Toronto')
                toutes_les_dates.append(tz.localize(dt))
        film["first_show"] = int(min(toutes_les_dates).timestamp()) if toutes_les_dates else None
        film["last_show"] = int(max(toutes_les_dates).timestamp()) if toutes_les_dates else None
    
    # Tri des films prochaine séance, puis par titre (sans accent)
    def sans_accents(texte):
        return unicodedata.normalize('NFKD', texte).encode('ASCII', 'ignore').decode('ASCII')

    films_list = list(films_dict.values())
    
    films_list.sort(key=lambda film: (
        film.get("first_show", 0),
        sans_accents(film.get("titre", "").lower())
    ))

    # Tri de la légende, Liste complète des attributs, sans filtrage
    legend_list = list(used_attributes.values())
    legend_list.sort(key=lambda attr: attr["ShortName"].lower())

    print(f"⚠️ Séances ignorées : {ignored_count}")

    return {
        "cinema": "Cinéma Centre-Ville",
        "legende": legend_list,
        "films": films_list
    }

# 🚀 Point d’entrée
TZ = ZoneInfo("America/Toronto")

def compute_checksum(data: dict) -> str:
    """Calcule un hash SHA256 sur la structure JSON (hors métadonnées)."""
    contenu = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(contenu.encode("utf-8")).hexdigest()

def load_previous_checksum(filepath: str) -> str | None:
    """Charge le checksum déjà présent dans films.json (si dispo)."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            contenu = json.load(f)
        return contenu.get("_meta", {}).get("checksum")
    except Exception:
        return None

def main():
    sessions = fetch_sessions()
    final_file = "films.json"
    temp_file = "films_temp.json"

    if not sessions:
        print("⚠️ Aucune séance récupérée, création d'un fichier vide.")
        return

    films = transform_data(sessions)

    # 1️⃣ Calcul du checksum sur la partie films
    new_checksum = compute_checksum({"films": films})

    # 2️⃣ Lecture de l'ancien checksum (dans films.json si présent)
    old_checksum = load_previous_checksum(final_file)

    # 3️⃣ Logs de debug
    print(f"Ancien checksum: {old_checksum}")
    print(f"Nouveau checksum: {new_checksum}")
    print(f"{final_file} existe ? {os.path.exists(final_file)}")

    # 4️⃣ Condition d'écriture
    if (old_checksum is None) or (old_checksum != new_checksum) or not os.path.exists(final_file):
        print("✏️  Écriture du fichier (nouveau checksum ou fichier manquant).")

        sortie = {
            "_meta": {
                "checksum": new_checksum,
                "derniere_mise_a_jour": datetime.now(TZ).isoformat()
            },
            "films": films
        }

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(sortie, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, final_file)
            print(f"✅ {final_file} mis à jour à {os.path.abspath(final_file)}")
        except Exception as e:
            print(f"❌ Erreur écriture {final_file} : {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            sys.exit(1)
    else:
        print("ℹ️ Aucun changement détecté, fichier inchangé.")


if __name__ == "__main__":
    main()

