import datetime
import logging
import os
from pathlib import Path
from typing import Optional

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
logger = logging.getLogger(__name__)

YANDEX_WEATHER_API_URL = "https://api.weather.yandex.ru/v2/informers"
OPEN_WEATHER_MAP_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_CACHE_HOURS = 6

TEMP_RECOMMENDATIONS = [
    (-100, -20, "Очень холодно. Нужны тёплая куртка, шапка и перчатки."),
    (-20, -10, "Холодно. Лучше выйти в зимней куртке и шарфе."),
    (-10, 0, "Прохладно. Подойдёт тёплая куртка или плотное пальто."),
    (0, 5, "Свежо. Лучше надеть куртку и закрытую обувь."),
    (5, 10, "Прохладно. Подойдёт ветровка или лёгкое пальто."),
    (10, 15, "Умеренно. Подойдут куртка, худи или плотный свитер."),
    (15, 20, "Комфортно. Достаточно лёгкой кофты поверх футболки."),
    (20, 25, "Тепло. Футболки или рубашки обычно достаточно."),
    (25, 30, "Жарко. Лучше выбрать лёгкую одежду и взять воду."),
    (30, 100, "Очень жарко. Нужны лёгкая одежда, вода и защита от солнца."),
]

WEATHER_ICONS = {
    "clear": "☀️",
    "partly-cloudy": "⛅",
    "cloudy": "☁️",
    "clouds": "☁️",
    "overcast": "☁️",
    "drizzle": "🌦️",
    "light-rain": "🌧️",
    "rain": "🌧️",
    "moderate-rain": "🌧️",
    "heavy-rain": "🌧️",
    "continuous-heavy-rain": "🌧️",
    "showers": "🌦️",
    "wet-snow": "🌨️",
    "light-snow": "❄️",
    "snow": "❄️",
    "snow-showers": "❄️",
    "hail": "🌨️",
    "mist": "☁️",
    "fog": "☁️",
    "haze": "☁️",
    "smoke": "☁️",
    "thunderstorm": "⛈️",
    "thunderstorm-with-rain": "⛈️",
    "thunderstorm-with-hail": "⛈️",
}

YANDEX_CONDITION_DESCRIPTIONS = {
    "clear": "ясно",
    "partly-cloudy": "малооблачно",
    "cloudy": "облачно с прояснениями",
    "overcast": "пасмурно",
    "drizzle": "морось",
    "light-rain": "небольшой дождь",
    "rain": "дождь",
    "moderate-rain": "умеренный дождь",
    "heavy-rain": "сильный дождь",
    "continuous-heavy-rain": "продолжительный сильный дождь",
    "showers": "ливень",
    "wet-snow": "дождь со снегом",
    "light-snow": "небольшой снег",
    "snow": "снег",
    "snow-showers": "снегопад",
    "hail": "град",
    "thunderstorm": "гроза",
    "thunderstorm-with-rain": "дождь с грозой",
    "thunderstorm-with-hail": "гроза с градом",
}


def _now() -> datetime.datetime:
    return datetime.datetime.now()


def _format_cached_at(value: datetime.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _parse_cached_at(value: str) -> datetime.datetime | None:
    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def normalize_weather_address(address: str) -> str:
    normalized = str(address).strip()
    if not normalized:
        return ""
    if "," in normalized or "перм" in normalized.lower():
        return normalized
    return f"Пермь, {normalized}"


def should_refresh_weather(cached_at: str, now: datetime.datetime | None = None) -> bool:
    cached_dt = _parse_cached_at(cached_at)
    if cached_dt is None:
        return True
    current = now or _now()
    return current - cached_dt >= datetime.timedelta(hours = WEATHER_CACHE_HOURS)


def get_weather_recommendation(temp_celsius: float) -> str:
    for min_temp, max_temp, recommendation in TEMP_RECOMMENDATIONS:
        if min_temp <= temp_celsius < max_temp:
            return recommendation
    return "Погода нестандартная, лучше ориентироваться по ситуации."


def _normalize_weather_payload(payload: dict, provider: str) -> dict:
    normalized = dict(payload)
    normalized["provider"] = provider
    return normalized


def get_weather_by_coords_openweathermap(latitude: float, longitude: float) -> Optional[dict]:
    if requests is None:
        logger.warning("requests is unavailable, weather API disabled")
        return None

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        logger.warning("OPENWEATHER_API_KEY не найден")
        return None

    try:
        response = requests.get(
            OPEN_WEATHER_MAP_URL,
            params = {
                "lat": latitude,
                "lon": longitude,
                "appid": api_key,
                "units": "metric",
                "lang": "ru",
            },
            timeout = 10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к OpenWeatherMap API")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка при обращении к OpenWeatherMap API: %s", exc)
        return None

    try:
        weather_entries = data.get("weather") or [{}]
        weather_data = weather_entries[0] if weather_entries else {}
        main_data = data.get("main", {})
        wind_data = data.get("wind", {})
        condition_key = str(weather_data.get("main", "")).lower()
        description = str(weather_data.get("description", "")).strip() or condition_key
        return _normalize_weather_payload(
            {
                "temp": round(float(main_data.get("temp", 0))),
                "feels_like": round(float(main_data.get("feels_like", 0))),
                "description": description,
                "icon": WEATHER_ICONS.get(condition_key, "🌡️"),
                "humidity": int(main_data.get("humidity", 0) or 0),
                "wind_speed": round(float(wind_data.get("speed", 0) or 0), 1),
                "city": str(data.get("name", "")),
            },
            provider = "openweather",
        )
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        logger.error("Ошибка при парсинге ответа OpenWeatherMap API: %s", exc)
        return None


def get_weather_by_coords_yandex(latitude: float, longitude: float) -> Optional[dict]:
    if requests is None:
        logger.warning("requests is unavailable, weather API disabled")
        return None

    api_key = os.getenv("YANDEX_WEATHER_API_KEY")
    if not api_key:
        logger.warning("YANDEX_WEATHER_API_KEY не найден")
        return None

    try:
        response = requests.get(
            YANDEX_WEATHER_API_URL,
            headers = {"X-Yandex-API-Key": api_key},
            params = {
                "lat": latitude,
                "lon": longitude,
                "lang": "ru_RU",
            },
            timeout = 10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к Яндекс.Погода API")
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка при обращении к Яндекс.Погода API: %s", exc)
        return None

    try:
        fact = data.get("fact", {})
        condition = str(fact.get("condition", "")).strip()
        return _normalize_weather_payload(
            {
                "temp": round(float(fact.get("temp", 0))),
                "feels_like": round(float(fact.get("feels_like", 0))),
                "description": YANDEX_CONDITION_DESCRIPTIONS.get(condition, condition or "погода"),
                "icon": WEATHER_ICONS.get(condition, "🌡️"),
                "humidity": int(fact.get("humidity", 0) or 0),
                "wind_speed": round(float(fact.get("wind_speed", 0) or 0), 1),
                "city": str(data.get("geo_object", {}).get("locality", {}).get("name", "")),
            },
            provider = "yandex",
        )
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        logger.error("Ошибка при парсинге ответа Яндекс.Погода API: %s", exc)
        return None


def get_weather_by_coords(latitude: float, longitude: float) -> Optional[dict]:
    weather = get_weather_by_coords_openweathermap(latitude, longitude)
    if weather is not None:
        return weather
    return get_weather_by_coords_yandex(latitude, longitude)


def resolve_coordinates_for_config(
    config_manager,
    force_refresh: bool = False,
) -> tuple[float, float] | None:
    from .geocoder_utils import get_coordinates_by_address

    address = normalize_weather_address(getattr(config_manager.config, "user_address", ""))
    if not address:
        return None

    cached = config_manager.get_user_coordinates()
    if cached is not None and not force_refresh:
        return cached

    coords = get_coordinates_by_address(address)
    if coords is None:
        return cached

    config_manager.set_user_coordinates(coords[0], coords[1])
    return coords


def get_weather_for_config(
    config_manager,
    force_refresh: bool = False,
    force_geocode: bool = False,
) -> Optional[dict]:
    coords = resolve_coordinates_for_config(
        config_manager,
        force_refresh = force_geocode,
    )
    if coords is None:
        return None

    cached_payload = getattr(config_manager.config, "weather_payload", {}) or {}
    cached_at = getattr(config_manager.config, "weather_cached_at", "")
    if cached_payload and not force_refresh and not should_refresh_weather(cached_at):
        return cached_payload

    longitude, latitude = coords
    weather = get_weather_by_coords(latitude, longitude)
    if weather is None:
        return cached_payload or None

    config_manager.set_weather_cache(weather, _format_cached_at(_now()))
    return weather


def get_weather_for_address(address: str) -> Optional[dict]:
    from .geocoder_utils import get_coordinates_by_address

    coords = get_coordinates_by_address(normalize_weather_address(address))
    if coords is None:
        logger.warning("Не удалось получить координаты для адреса: %s", address)
        return None

    longitude, latitude = coords
    return get_weather_by_coords(latitude, longitude)
