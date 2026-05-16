"""
Пример использования геокодера для получения координат по адресу.

Этот файл демонстрирует, как использовать функцию get_coordinates_by_address
в вашем Flet приложении.
"""

from app.utils.geocoder_utils import get_coordinates_by_address, get_address_info


def example_get_coordinates():
    """Пример 1: Получение координат по адресу"""
    address = "Москва, Красная площадь"
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
        print(f"  Название: {info['name']}")
        print(f"  Описание: {info['description']}")
        print(f"  Адрес: {info['address']}")
        print(f"  Координаты: {info['coordinates']}")
        print(f"  Населенный пункт: {info['locality']}")
    else:
        print(f"Адрес не найден: {address}")

if __name__ == "__main__":
    print("=" * 60)
    print("Пример 1: Получение координат")
    print("=" * 60)
    example_get_coordinates()
    
    print("\n" + "=" * 60)
    print("Пример 2: Получение полной информации об адресе")
    print("=" * 60)
    example_get_address_info()