import requests
from typing import Tuple, Optional
import logging
import os

logger = logging.getLogger(__name__)

YANDEX_GEOCODER_API_URL = "https://geocode-maps.yandex.ru/1.x"


def get_coordinates_by_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Получает координаты (широта, долгота) по адресу используя Yandex Geocoder API.
    
    Args:
        address: Адрес для геокодирования (строка)
        
    Returns:
        Кортеж (longitude, latitude) если адрес найден, иначе None
        
    Example:
        >>> coords = get_coordinates_by_address("Москва, Красная площадь")
        >>> print(coords)
        (37.6173, 55.7558)
    """
    try:
        api_key = os.getenv("YANDEX_GEOCODER_API_KEY", "66b0d80b-b232-44da-95e5-8b67fbbc59df")
        params = {
            "apikey": api_key,
            "geocode": address,
            "format": "json",
            "lang": "ru"
        }
        
        response = requests.get(YANDEX_GEOCODER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем, нашли ли мы адрес
        if data.get("response", {}).get("GeoObjectCollection", {}).get("metaDataProperty", {}).get("GeocoderResponseMetaData", {}).get("found", "0") == "0":
            logger.warning(f"Адрес не найден: {address}")
            return None
        
        # Извлекаем координаты первого найденного результата
        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            logger.warning(f"Не удалось получить координаты для адреса: {address}")
            return None
        
        # Координаты в формате "longitude latitude"
        coordinates_str = features[0].get("GeoObject", {}).get("Point", {}).get("pos", "")
        if not coordinates_str:
            logger.warning(f"Координаты отсутствуют в ответе для адреса: {address}")
            return None
        
        # Парсим координаты
        coords = coordinates_str.split()
        if len(coords) == 2:
            longitude = float(coords[0])
            latitude = float(coords[1])
            logger.info(f"Найдены координаты для '{address}': ({longitude}, {latitude})")
            return (longitude, latitude)
        
        return None
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout при обращении к Yandex Geocoder API для адреса: {address}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Yandex Geocoder API: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге ответа от API для адреса '{address}': {e}")
        return None


def get_address_info(address: str) -> Optional[dict]:
    """
    Получает полную информацию об адресе включая координаты, название объекта и другую информацию.
    
    Args:
        address: Адрес для геокодирования (строка)
        
    Returns:
        Словарь с информацией об адресе или None, если адрес не найден
        
    Example:
        >>> info = get_address_info("Москва, ул. Красная")
        >>> print(info)
        {
            'coordinates': (37.6173, 55.7558),
            'name': 'Красная площадь, Москва',
            'address': 'Москва, Центральный административный округ',
            ...
        }
    """
    try:
        api_key = os.getenv("YANDEX_GEOCODER_API_KEY", "66b0d80b-b232-44da-95e5-8b67fbbc59df")
        params = {
            "apikey": api_key,
            "geocode": address,
            "format": "json",
            "lang": "ru"
        }
        
        response = requests.get(YANDEX_GEOCODER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем, нашли ли мы адрес
        if data.get("response", {}).get("GeoObjectCollection", {}).get("metaDataProperty", {}).get("GeocoderResponseMetaData", {}).get("found", "0") == "0":
            logger.warning(f"Адрес не найден: {address}")
            return None
        
        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            return None
        
        geo_object = features[0].get("GeoObject", {})
        
        # Извлекаем координаты
        coordinates_str = geo_object.get("Point", {}).get("pos", "")
        if not coordinates_str:
            return None
        
        coords = coordinates_str.split()
        if len(coords) != 2:
            return None
        
        longitude = float(coords[0])
        latitude = float(coords[1])
        
        # Собираем информацию об адресе
        meta_data = geo_object.get("metaDataProperty", {}).get("GeocoderMetaData", {})
        address_details = meta_data.get("Address", {})
        
        info = {
            "coordinates": (longitude, latitude),
            "name": geo_object.get("name", ""),
            "description": geo_object.get("description", ""),
            "address": address_details.get("formatted", ""),
            "country": address_details.get("country_code", ""),
            "administrative_area": address_details.get("AdministrativeAreaName", ""),
            "locality": address_details.get("LocalityName", ""),
            "thoroughfare": address_details.get("ThoroughfareName", ""),
            "premise": address_details.get("PremiseName", ""),
        }
        
        logger.info(f"Получена полная информация об адресе: {address}")
        return info
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout при обращении к Yandex Geocoder API для адреса: {address}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Yandex Geocoder API: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге ответа от API для адреса '{address}': {e}")
        return None
