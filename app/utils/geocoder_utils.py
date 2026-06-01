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
YANDEX_GEOCODER_API_URL = "https://geocode-maps.yandex.ru/1.x"


def get_coordinates_by_address(address: str) -> Optional[tuple[float, float]]:
    if requests is None:
        logger.warning("requests is unavailable, geocoder disabled")
        return None

    try:
        response = requests.get(
            YANDEX_GEOCODER_API_URL,
            params = {
                "apikey": os.getenv("YANDEX_GEOCODER_API_KEY"),
                "geocode": address,
                "format": "json",
                "lang": "ru",
            },
            timeout = 10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к Yandex Geocoder API для адреса: %s", address)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка при обращении к Yandex Geocoder API: %s", exc)
        return None

    try:
        meta = data.get("response", {}).get("GeoObjectCollection", {}).get("metaDataProperty", {})
        found = meta.get("GeocoderResponseMetaData", {}).get("found", "0")
        if found == "0":
            logger.warning("Адрес не найден: %s", address)
            return None

        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            logger.warning("Координаты для адреса не найдены: %s", address)
            return None

        position = features[0].get("GeoObject", {}).get("Point", {}).get("pos", "")
        longitude_text, latitude_text = position.split()
        coordinates = float(longitude_text), float(latitude_text)
        logger.info("Найдены координаты для '%s': %s", address, coordinates)
        return coordinates
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        logger.error("Ошибка при парсинге ответа геокодера для '%s': %s", address, exc)
        return None


def get_address_info(address: str) -> Optional[dict]:
    if requests is None:
        logger.warning("requests is unavailable, geocoder disabled")
        return None

    try:
        response = requests.get(
            YANDEX_GEOCODER_API_URL,
            params = {
                "apikey": os.getenv("YANDEX_GEOCODER_API_KEY"),
                "geocode": address,
                "format": "json",
                "lang": "ru",
            },
            timeout = 10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к Yandex Geocoder API для адреса: %s", address)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Ошибка при обращении к Yandex Geocoder API: %s", exc)
        return None

    try:
        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            return None

        geo_object = features[0].get("GeoObject", {})
        position = geo_object.get("Point", {}).get("pos", "")
        longitude_text, latitude_text = position.split()
        address_details = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {}).get("Address", {})

        return {
            "coordinates": (float(longitude_text), float(latitude_text)),
            "name": geo_object.get("name", ""),
            "description": geo_object.get("description", ""),
            "address": address_details.get("formatted", ""),
            "country": address_details.get("country_code", ""),
            "administrative_area": address_details.get("AdministrativeAreaName", ""),
            "locality": address_details.get("LocalityName", ""),
            "thoroughfare": address_details.get("ThoroughfareName", ""),
            "premise": address_details.get("PremiseName", ""),
        }
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        logger.error("Ошибка при парсинге адресной информации для '%s': %s", address, exc)
        return None
