import requests
from typing import Tuple, Optional
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

# Важные начальные объявления
load_dotenv(Path(__file__).resolve().parent.parent.parent / "app/utils/config.env")
logger = logging.getLogger(__name__)
YANDEX_GEOCODER_API_URL = "https://geocode-maps.yandex.ru/1.x"


def get_coordinates_by_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Получает координаты (широта, долгота) по адресу используя Yandex Geocoder API.
    
    Args:
        address: Адрес для геокодирования (строка)
        
    Returns:
        tuple (longitude, latitude) если адрес найден, иначе None
        
    Example:
        >>> coords = get_coordinates_by_address("Москва, Красная площадь")
        >>> print(coords)
        (37.6173, 55.7558)
    """
    try:
        api_key = os.getenv("YANDEX_GEOCODER_API_KEY")
        params = {
            "apikey": api_key,
            "geocode": address,
            "format": "json",
            "lang": "ru"
        }
        
        response = requests.get(YANDEX_GEOCODER_API_URL, params = params, timeout = 10)
        response.raise_for_status()
        
        data = response.json()
        
        # Проверяем, нашли ли мы адрес
        if data.get("response", {}).get("GeoObjectCollection", {}).get("metaDataProperty", {}).get("GeocoderResponseMetaData", {}).get("found", "0") == "0":
            logger.warning(f"Адрес не найден: {address}")
            return
        
        # Извлекаем координаты первого найденного результата
        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            logger.warning(f"Не удалось получить координаты для адреса: {address}")
            return
        
        # Координаты в формате "longitude latitude"
        coordinates_str = features[0].get("GeoObject", {}).get("Point", {}).get("pos", "")
        if not coordinates_str:
            logger.warning(f"Координаты отсутствуют в ответе для адреса: {address}")
            return
        
        # Парсим координаты
        coords = coordinates_str.split()
        if len(coords) == 2:
            longitude = float(coords[0])
            latitude = float(coords[1])
            logger.info(f"Найдены координаты для '{address}': ({longitude}, {latitude})")
            return (longitude, latitude)
        return
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout при обращении к Yandex Geocoder API для адреса: {address}")
        return
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Yandex Geocoder API: {e}")
        return
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге ответа от API для адреса '{address}': {e}")
        return


def get_address_info(address: str) -> Optional[dict]:
    """
    Получает полную информацию об адресе включая координаты, название объекта и другую информацию.
    
    Args:
        address: Адрес для геокодирования (строка)
        
    Returns:
        dict с информацией об адресе или None, если адрес не найден
        
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
        api_key = os.getenv("YANDEX_GEOCODER_API_KEY")
        params = {
            "apikey": api_key,
            "geocode": address,
            "format": "json",
            "lang": "ru"
        }
        
        response = requests.get(YANDEX_GEOCODER_API_URL, params = params, timeout = 10)
        response.raise_for_status()
        
        data = response.json()
        
        # Проверка: найден ли адрес
        if data.get("response", {}).get("GeoObjectCollection", {}).get("metaDataProperty", {}).get("GeocoderResponseMetaData", {}).get("found", "0") == "0":
            logger.warning(f"Адрес не найден: {address}")
            return
        
        features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
        if not features:
            return
        
        geo_object = features[0].get("GeoObject", {})
        
        # Извлечение координат
        coordinates_str = geo_object.get("Point", {}).get("pos", "")
        if not coordinates_str:
            return
        
        coords = coordinates_str.split()
        if len(coords) != 2:
            return
        
        longitude = float(coords[0])
        latitude = float(coords[1])
        
        # Сбор информации об адресе
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
        return
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Yandex Geocoder API: {e}")
        return
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге ответа от API для адреса '{address}': {e}")
        return


# Простые функции для примеры использования
def example_get_coordinates():
    """Пример 1: Получение координат по адресу"""
    address = "Пермь, улица Малкова, 26"
    coordinates = get_coordinates_by_address(address)
    
    if coordinates:
        longitude, latitude = coordinates
        print(f"Адрес: {address}")
        print(f"Координаты: {latitude}, {longitude}")
        print(f"Ссылка на карту: https://yandex.ru/maps/?ll={longitude},{latitude}&z=15&pt={longitude},{latitude},pm2lbm")
    else:
        print(f"Не удалось найти координаты для адреса: {address}")


def example_get_address_info():
    """Пример 2: Получение полной информации об адресе"""
    address = "Санкт-Петербург, Невский проспект, 1"
    info = get_address_info(address)
    
    if info:
        print(f"Найдена информация об адресе:")
        print(f"\tНазвание: {info['name']}")
        print(f"\tОписание: {info['description']}")
        print(f"\tАдрес: {info['address']}")
        print(f"\tКоординаты: {info['coordinates']}")
        print(f"\tНаселенный пункт: {info['locality']}")
    else:
        print(f"Адрес не найден: {address}")



# Пример использования геокодера для получения координат по адресу.
if __name__ == "__main__":
        print("=" * 60)
        print("Пример 1: Получение координат")
        print("=" * 60)
        example_get_coordinates()
        
        # print("\n" + "=" * 60)
        # print("Пример 2: Получение полной информации об адресе")
        # print("=" * 60)
        # example_get_address_info()