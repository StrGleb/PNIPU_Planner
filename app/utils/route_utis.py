from dotenv import load_dotenv
import requests
import os
from pathlib import Path

load_dotenv((Path(__file__).resolve().parent.parent / "config.env").resolve())
API_KEY = os.getenv("DOUBLE_GIS_API_KEY")

def get_route(start, end, transport):
    """
    start, end: tuple (lat, lon)
    transport: "pedestrian" | "driving" | "public_transport"
    """
    
    if transport == "public_transport":
        url = f"https://routing.api.2gis.com/public_transport/2.0?key={API_KEY}"
        payload = {
            "source": {"point": {"lat": start[0], "lon": start[1]}},
            "target": {"point": {"lat": end[0], "lon": end[1]}},
            "transport": ["bus", "tram"],
            "locale": "ru",
            "output": "summary"
        }
    else:
        # Routing API для авто/пешком
        url = f"https://routing.api.2gis.com/routing/7.0.0/global?key={API_KEY}"
        payload = {
            "points": [
                {"lat": start[0], "lon": start[1]},
                {"lat": end[0], "lon": end[1]}
            ],
            "transport": transport,
            "output": "summary"
        }
    
    if not API_KEY:
        return None

    try:
        resp = requests.post(url, json = payload, timeout = 10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return None

    if type(data) == list:
        return [data[0]['total_distance'], data[0]['total_duration']]
    else:
        if data.get("status") == "OK" and data.get("result"):
            r = data["result"][0]
            return {
                "duration_min": r["duration"] // 60,
                "distance_km": r["length"] / 1000
            }
    return None



# Использование:
if __name__ == "__main__":
    point_a = {'lat': 57.997622, 'lon': 56.193610}
    point_b = {'lat': 58.054531, 'lon': 56.222769}
    walking = get_route((point_a["lat"], point_a["lon"]), (point_b["lat"], point_b["lon"]), "pedestrian")
    car = get_route((point_a["lat"], point_a["lon"]), (point_b["lat"], point_b["lon"]), "driving")
    bus = get_route((point_a["lat"], point_a["lon"]), (point_b["lat"], point_b["lon"]), "public_transport")
    print(walking) # Пример возвращаемого значения {'duration_min': 119, 'distance_km': 10.731}, первое время в минутах, второе дистанция в км
    print(car) # Пример возвращаемого значения: {'duration_min': 119, 'distance_km': 10.731}, первое время в минутах, второе дистанция в км
    print(bus) # Пример возвращаемого значения: [10723, 6013] - первое время с ожиданием атобуса в секундах, второе время вообще без ожидания тоже в секундах
