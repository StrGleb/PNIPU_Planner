import os
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv((Path(__file__).resolve().parent.parent / "config.env").resolve())


def get_route(start, end, transport) -> None | list[int] | dict:
    if requests is None:
        return None

    api_key = os.getenv("DOUBLE_GIS_API_KEY")
    if not api_key:
        return None

    if transport == "public_transport":
        url = f"https://routing.api.2gis.com/public_transport/2.0?key={api_key}"
        payload = {
            "source": {"point": {"lat": start[0], "lon": start[1]}},
            "target": {"point": {"lat": end[0], "lon": end[1]}},
            "transport": ["bus", "tram"],
            "locale": "ru",
            "output": "summary",
        }
    else:
        url = f"https://routing.api.2gis.com/routing/7.0.0/global?key={api_key}"
        payload = {
            "points": [
                {"lat": start[0], "lon": start[1]},
                {"lat": end[0], "lon": end[1]},
            ],
            "transport": transport,
            "output": "summary",
        }

    try:
        response = requests.post(url, json = payload, timeout = 10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None

    if isinstance(data, list) and data:
        return [data[0]["total_distance"], data[0]["total_duration"]]

    if isinstance(data, dict) and data.get("status") == "OK" and data.get("result"):
        route = data["result"][0]
        return {
            "duration_min": route["duration"] // 60,
            "distance_km": route["length"] / 1000,
        }

    return None
