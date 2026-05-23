import requests
import logging
import os
from dotenv import load_dotenv
from typing import Optional, Dict

# Загружаем переменные окружения
load_dotenv(r"app\utils\config.env")
logger = logging.getLogger(__name__)

YANDEX_WEATHER_API_URL = "https://api.weather.yandex.ru/v2/informers"

# Рекомендации по температуре
TEMP_RECOMMENDATIONS = [
    (-100, -20, "Очень холодно! Наденьте тёплую зимнюю куртку, шапку, шарф и варежки. Не забудьте термобельё."),
    (-20, -10, "Холодно. Тёплая зимняя куртка, шапка и шарф обязательны."),
    (-10, 0, "Прохладно. Наденьте зимнюю или осеннюю куртку, шапку."),
    (0, 5, "Прохладно. Осенняя куртка или пальто, можно лёгкую шапку."),
    (5, 10, "Прохладно. Ветровка или лёгкое пальто, шарф по желанию."),
    (10, 15, "Умеренно. Лёгкая куртка, ветровка или свитер."),
    (15, 20, "Комфортно. Футболка с лёгкой кофтой или ветровкой."),
    (20, 25, "Тепло. Можно надеть футболку или рубашку с коротким рукавом."),
    (25, 30, "Жарко. Лёгкая одежда из натуральных тканей, головной убор от солнца."),
    (30, 100, "Очень жарко! Максимально лёгкая одежда, обязательно головной убор и вода."),
]

# Иконки погоды для Flet (маппинг условий Яндекса)
WEATHER_ICONS = {
    "clear": "☀️",           # ясно
    "partly-cloudy": "⛅",   # малооблачно
    "cloudy": "☁️",          # облачно с прояснениями
    "overcast": "☁️",        # пасмурно
    "drizzle": "🌦️",         # моросящий дождь
    "light-rain": "🌧️",      # небольшой дождь
    "rain": "🌧️",            # дождь
    "moderate-rain": "🌧️",   # умеренный дождь
    "heavy-rain": "🌧️",      # сильный дождь
    "continuous-heavy-rain": "🌧️", # продолжительный сильный дождь
    "showers": "🌦️",         # ливень
    "wet-snow": "🌨️",        # дождь со снегом
    "light-snow": "❄️",      # небольшой снег
    "snow": "❄️",            # снег
    "snow-showers": "❄️",    # снежные ливни
    "hail": "🌨️",            # град
    "thunderstorm": "⛈️",    # гроза
    "thunderstorm-with-rain": "⛈️", # дождь с грозой
    "thunderstorm-with-hail": "⛈️", # гроза с градом
}


def get_weather_recommendation(temp_celsius: float) -> str:
    """
    Возвращает рекомендацию по одежде на основе температуры.

    Args:
        temp_celsius: Температура в градусах Цельсия

    Returns:
        Строка с рекомендацией по одежде
    """
    for min_temp, max_temp, recommendation in TEMP_RECOMMENDATIONS:
        if min_temp <= temp_celsius < max_temp:
            return recommendation
    return "Погода необычная, оденьтесь по ситуации!"


def get_weather_by_coords(latitude: float, longitude: float) -> Optional[Dict]:
    """
    Получает текущую погоду по координатам используя Яндекс.Погода API.

    Args:
        latitude: Широта
        longitude: Долгота

    Returns:
        dict с информацией о погоде или None, если произошла ошибка
        {
            'temp': температура (°C),
            'feels_like': ощущается как (°C),
            'description': описание погоды,
            'icon': иконка погоды,
            'humidity': влажность (%),
            'wind_speed': скорость ветра (м/с),
        }
    """
    try:
        api_key = os.getenv("YANDEX_WEATHER_API_KEY")
        if not api_key:
            logger.warning("YANDEX_WEATHER_API_KEY не найден в переменных окружения")
            return None

        headers = {
            "X-Yandex-API-Key": api_key
        }

        params = {
            "lat": latitude,
            "lon": longitude,
            "lang": "ru_RU",
        }

        response = requests.get(YANDEX_WEATHER_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Извлекаем данные о погоде из ответа Яндекса
        fact = data.get("fact", {})

        temp = fact.get("temp", 0)
        feels_like = fact.get("feels_like", 0)
        humidity = fact.get("humidity", 0)
        wind_speed = fact.get("wind_speed", 0)
        condition = fact.get("condition", "")

        icon = WEATHER_ICONS.get(condition, "🌡️")

        # Формируем описание на русском языке
        condition_descriptions = {
            "clear": "ясно",
            "partly-cloudy": "малооблачно",
            "cloudy": "облачно с прояснениями",
            "overcast": "пасмурно",
            "drizzle": "моросящий дождь",
            "light-rain": "небольшой дождь",
            "rain": "дождь",
            "moderate-rain": "умеренный дождь",
            "heavy-rain": "сильный дождь",
            "continuous-heavy-rain": "продолжительный сильный дождь",
            "showers": "ливень",
            "wet-snow": "дождь со снегом",
            "light-snow": "небольшой снег",
            "snow": "снег",
            "snow-showers": "снежные ливни",
            "hail": "град",
            "thunderstorm": "гроза",
            "thunderstorm-with-rain": "дождь с грозой",
            "thunderstorm-with-hail": "гроза с градом",
        }

        description = condition_descriptions.get(condition, condition)

        result = {
            "temp": round(temp),
            "feels_like": round(feels_like),
            "description": description,
            "icon": icon,
            "humidity": humidity,
            "wind_speed": round(wind_speed, 1),
            "city": data.get("geo_object", {}).get("locality", {}).get("name", ""),
        }

        logger.info(f"Получена погода для координат ({latitude}, {longitude}): {result}")
        return result

    except requests.exceptions.Timeout:
        logger.error("Timeout при обращении к Яндекс.Погода API")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Яндекс.Погода API: {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге ответа от API: {e}")
        return None


def get_weather_for_address(address: str) -> Optional[Dict]:
    """
    Получает погоду по адресу (сначала геокодирует адрес, затем получает погоду).

    Args:
        address: Адрес для получения погоды

    Returns:
        dict с информацией о погоде или None
    """
    from .geocoder_utils import get_coordinates_by_address

    coords = get_coordinates_by_address(address)
    if not coords:
        logger.warning(f"Не удалось получить координаты для адреса: {address}")
        return None

    longitude, latitude = coords
    return get_weather_by_coords(latitude, longitude)


def example_get_weather():
    """Пример получения погоды по координатам (Пермь)"""
    # Координаты Перми
    latitude = 58.0105
    longitude = 56.2502

    weather = get_weather_by_coords(latitude, longitude)

    if weather:
        print(f"Город: {weather['city']}")
        print(f"Температура: {weather['temp']}°C (ощущается как {weather['feels_like']}°C)")
        print(f"Погода: {weather['icon']} {weather['description']}")
        print(f"Влажность: {weather['humidity']}%")
        print(f"Ветер: {weather['wind_speed']} м/с")
        print(f"Рекомендация: {get_weather_recommendation(weather['temp'])}")
    else:
        print("Не удалось получить данные о погоде")


if __name__ == "__main__":
    print("=" * 60)
    print("Пример получения погоды")
    print("=" * 60)
    example_get_weather()