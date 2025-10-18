import sys
import requests
import json
import locale
from datetime import date, datetime, timedelta
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

def trier_films_par_prochaine_seance(films_dict):
    tz = pytz.timezone("America/Toronto")
    now = datetime.now(tz)
    today = now.date()

    films_ouverts = []
    films_a_venir = []

    for film in films_dict.values():
        opening_str = film.get("OpeningDate", "")
        try:
            opening_date = datetime.strptime(opening_str, "%Y-%m-%d").date()
        except ValueError:
            opening_date = today

        if opening_date > today:
            films_a_venir.append(film)
            continue

        horaires = film.get("horaire", {})
        seances_futures = []

        for jour_str, heures in horaires.items():
            try:
                jour = datetime.strptime(jour_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            for h in heures:
                try:
                    dt = tz.localize(datetime.strptime(f"{jour_str} {h['heure']}", "%Y-%m-%d %H:%M"))
                    if dt >= now:
                        seances_futures.append(dt)
                except Exception:
                    continue

        prochaine = min(seances_futures) if seances_futures else tz.localize(datetime(2100, 1, 1, 0, 0))
        films_ouverts.append((prochaine, film["titre"].lower(), film))

    # Tri des films ouverts par prochaine séance, puis par titre
    films_ouverts.sort(key=lambda x: (x[0], x[1]))
    films_ouverts = [f[2] for f in films_ouverts]

    # Tri des films à venir par titre
    films_a_venir.sort(key=lambda f: f["titre"].lower())

    return films_ouverts + films_a_venir

# 🧠 Transforme les données en JSON enrichi
def transform_data(sessions):
    films_dict = {}
    attribute_cache = {}
    used_attributes = {}
    ignored_count = 0

    tz = pytz.timezone('America/Toronto')
    now = datetime.now(tz)
    threshold = now + timedelta(minutes=0)
    # now = datetime.now(tz).date()  # 👈 On ne garde que la date
    
    # Format : Jour/Mois/Année Heure:Minute
    # formatted_threshold = threshold.strftime("%d/%m/%Y %H:%M")

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

    # Configuration du locale pour le tri avec les accents
    locale.setlocale(locale.LC_ALL, 'fr_CA.UTF-8')
    # Tri des films à l'affiche par titre en ordre alphabétique, puis par jours/heures
    films_tries = sorted(films_dict.values(), key=lambda f: locale.strxfrm(f["titre"]))

    # Tri des films à l'affiche par jours/heures
    # for film in films_dict.values():
    for film in films_tries:
        # Tri des jours (dates)
        film["horaire"] = dict(sorted(film["horaire"].items(), key=lambda x: x[0]))

        # Tri des séances par heure pour chaque jour
        for jour in film["horaire"]:
            film["horaire"][jour].sort(key=lambda s: s["heure"])

        # Calcul de la dernière séance
        toutes_les_dates = []
        for jour, seances in film["horaire"].items():
            for s in seances:
                dt = datetime.strptime(f"{jour} {s['heure']}", "%Y-%m-%d %H:%M")
                tz = pytz.timezone('America/Toronto')
                toutes_les_dates.append(tz.localize(dt))
        film["last_show"] = int(max(toutes_les_dates).timestamp()) if toutes_les_dates else None

    # Tri des films bientôt à l'affiche
    # films_list = list(films_dict.values())
    # films_list.sort(key=lambda film: film["titre"].lower())
    films_list = trier_films_par_prochaine_seance(films_dict)

    # Tri de la légende, Liste complète des attributs, sans filtrage
    legend_list = list(used_attributes.values())
    legend_list.sort(key=lambda attr: attr["ShortName"].lower())

    print(f"⚠️ Séances ignorées : {ignored_count}")

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
    
    final_file = "films.json"
    checksum_file = "checksumfilms.json"
    temp_file = "films_temp.json"
    
    if not sessions:
        print("⚠️ Aucune séance récupérée, création d'un fichier vide.")
        return  # on sort proprement de main()

    data = transform_data(sessions)

    # 1️⃣ Calcul du checksum sur la structure JSON
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    new_checksum = compute_checksum(content_str)

    # 2️⃣ Lecture de l'ancien checksum (s'il existe)
    old_checksum = load_previous_checksum(checksum_file)

    # 3️⃣ Logs de debug
    print(f"Ancien checksum: {old_checksum}")
    print(f"Nouveau checksum: {new_checksum}")
    print(f"films.json existe ? {os.path.exists(final_file)}")
    print(f"checksumfilms.json existe ? {os.path.exists(checksum_file)}")

    # 4️⃣ Condition d'écriture
    if (old_checksum is None) or (old_checksum != new_checksum) or not os.path.exists(final_file):
        print("✏️  Écriture des fichiers (nouveau checksum ou fichier manquant).")

        # Écriture de films.json
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content_str)
            os.replace(temp_file, final_file)
            print(f"✅ {final_file} mis à jour à {os.path.abspath(final_file)}")
        except Exception as e:
            print(f"❌ Erreur écriture {final_file} : {e}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
            sys.exit(1)

        # Écriture du checksum
        save_checksum(checksum_file, new_checksum)
        print(f"✅ {checksum_file} mis à jour à {os.path.abspath(checksum_file)}")

    else:
        print("ℹ️ Aucun changement détecté, fichiers inchangés.")

if __name__ == "__main__":
    main()

