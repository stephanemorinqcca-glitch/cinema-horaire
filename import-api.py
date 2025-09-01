#!/usr/bin/env python3
# soap_to_films.py
import sys
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# 1. Configuration
TOKEN       = "n8gzfgxf2kzmba12gtkav92g24"
SOAP_URL    = "https://my.useast.veezi.com/WSVistaProjection/Service.svc"
OUTPUT_FILE = "films.json"

# 2. Fonction SOAP GetSchedule
def get_schedule_xml(start_date: str, end_date: str) -> bytes:
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema"
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <GetSchedule xmlns="http://www.veezi.com/WSVistaProjection">
      <siteToken>{TOKEN}</siteToken>
      <startDate>{start_date}</startDate>
      <endDate>{end_date}</endDate>
    </GetSchedule>
  </soap:Body>
</soap:Envelope>"""
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://www.veezi.com/WSVistaProjection/IService/GetSchedule"
    }
    resp = requests.post(SOAP_URL, data=envelope, headers=headers)
    resp.raise_for_status()
    return resp.content

# 3. Parser XML en données Python
def parse_schedule(xml_bytes: bytes) -> dict:
    # Namespace SOAP + service
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "v":    "http://www.veezi.com/WSVistaProjection"
    }
    root = ET.fromstring(xml_bytes)
    # Descendre jusqu'à GetScheduleResult → Schedule → Session
    sessions = root.find(".//v:GetScheduleResult/v:Schedule", ns)
    films_map = {}

    for s in sessions.findall("v:Session", ns):
        fid       = s.findtext("v:FilmId",       default="", namespaces=ns)
        title     = s.findtext("v:FilmTitle",    default="", namespaces=ns)
        rating    = s.findtext("v:Rating",       default="", namespaces=ns)
        duration  = s.findtext("v:Duration",     default="", namespaces=ns)
        poster    = s.findtext("v:FilmImageUrl", default="", namespaces=ns)
        # Genres multiples
        genres_el = s.find("v:Genres", ns)
        genres    = [g.text or "" for g in genres_el.findall("v:Genre", ns)] if genres_el is not None else []

        # ShowTime en ISO → format FR
        raw_dt = s.findtext("v:ShowTime", default="", namespaces=ns)
        try:
            dt        = datetime.fromisoformat(raw_dt)
            horaire   = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            horaire   = raw_dt

        # Regrouper par film
        if fid not in films_map:
            films_map[fid] = {
                "titre":          title,
                "classification": rating,
                "duree":          duration,
                "genre":          genres,
                "poster":         poster,
                "horaire":        []
            }
        films_map[fid]["horaire"].append(horaire)

    return films_map

# 4. Génération de films.json
def build_and_save_json(films_map: dict):
    output = {
        "cinema":      "Cinéma Centre-Ville",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "films":       []
    }
    for film in films_map.values():
        film["horaire"] = sorted(film["horaire"])
        output["films"].append(film)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

# 5. Point d’entrée
def main():
    # Dates en args ou par défaut : aujourd’hui → +30 jours
    today = datetime.today().strftime("%Y-%m-%d")
    start = sys.argv[1] if len(sys.argv)>1 else today
    default_end = (datetime.today() + timedelta(days=30)).strftime("%Y-%m-%d")
    end   = sys.argv[2] if len(sys.argv)>2 else default_end

    print(f"↻ Récupération des séances du {start} au {end}…")
    xml_bytes   = get_schedule_xml(start, end)
    films_map   = parse_schedule(xml_bytes)
    build_and_save_json(films_map)
    print(f"✅ {len(films_map)} films exportés dans {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
