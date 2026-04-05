# Alarm DLL — инструкция для фронтенда (Python/Flet)

## 📌 Что это

Это C++ библиотека (DLL), которая рассчитывает:

* время выхода
* время будильника

Фронт (Python/Flet) **не работает с C++ напрямую**, а вызывает одну функцию через DLL.

---

# 🔗 Единственная точка входа (контракт)

## Функция

```cpp
int calculate_alarm(
    const char* event_time,
    int travel_time,
    int prep_minutes,
    int buffer_time,
    bool use_weather,
    double weather_multiplier,
    bool round_to_five,
    char* out_alarm_time,
    int out_alarm_time_size,
    char* out_leave_time,
    int out_leave_time_size,
    char* out_comment,
    int out_comment_size
);
```

---

# 📥 Входные параметры

### 1. Время события

```text
event_time: "HH:MM"
```

Примеры:

* ✅ "08:30"
* ✅ "13:05"
* ❌ "8:30"
* ❌ "25:00"

---

### 2. Числовые параметры

```text
travel_time    → минуты на дорогу
prep_minutes   → минуты на сборы
buffer_time    → буфер (мин)
```

👉 должны быть **>= 0**

---

### 3. Погода

```text
use_weather         → учитывать или нет
weather_multiplier  → коэффициент
```

👉 `weather_multiplier >= 1.0`

---

### 4. Округление

```text
round_to_five → округлять ли до 5 минут вниз
```

---

# 📤 Выходные данные

Функция возвращает:

### 🔹 Код (`int`)

```text
0 — успех
1 — event_time == null
2 — ошибка входных данных
3 — неизвестная ошибка
```

---

### 🔹 Результаты (через буферы)

```text
out_alarm_time → "07:00"
out_leave_time → "07:42"
out_comment    → текст
```

---

# ⚠️ ВАЖНО ДЛЯ PYTHON

## 1. Строку передавать как bytes

```python
event_time.encode("utf-8")
```

❌ нельзя:

```python
"08:30"
```

---

## 2. Буферы создавать вручную

```python
from ctypes import create_string_buffer

alarm_buf = create_string_buffer(64)
leave_buf = create_string_buffer(64)
comment_buf = create_string_buffer(256)
```

---

## 3. После вызова декодировать

```python
alarm_buf.value.decode("utf-8")
```

---

## 4. DLL и Python должны совпадать по архитектуре

```text
DLL x64 → Python x64
DLL x86 → Python x86
```

---

# 🧪 Пример вызова

```python
import ctypes
from ctypes import *

dll = ctypes.CDLL(r"C:\path\to\planner_app.dll")

dll.calculate_alarm.argtypes = [
    c_char_p,
    c_int,
    c_int,
    c_int,
    c_bool,
    c_double,
    c_bool,
    c_void_p,
    c_int,
    c_void_p,
    c_int,
    c_void_p,
    c_int
]

dll.calculate_alarm.restype = c_int

alarm_buf = create_string_buffer(64)
leave_buf = create_string_buffer(64)
comment_buf = create_string_buffer(256)

code = dll.calculate_alarm(
    b"08:30",
    40,
    30,
    10,
    True,
    1.2,
    True,
    alarm_buf,
    len(alarm_buf),
    leave_buf,
    len(leave_buf),
    comment_buf,
    len(comment_buf)
)

if code == 0:
    print("Leave:", leave_buf.value.decode())
    print("Alarm:", alarm_buf.value.decode())
    print("Comment:", comment_buf.value.decode())
else:
    print("Error:", code)
```

---

# ❌ Частые ошибки

## 1. DLL не загружается

```text
OSError: cannot load library
```

Причины:

* неправильный путь
* разная разрядность
* DLL не собрана

---

## 2. Функция не найдена

```text
AttributeError: function not found
```

Причины:

* неправильная DLL
* старая версия DLL

---

## 3. Код ошибки 2

```text
некорректные данные
```

Проверить:

* формат времени
* отрицательные значения
* коэффициент < 1

---

# 📌 Что фронт НЕ должен делать

❌ работать с C++ классами
❌ передавать `std::string`
❌ менять порядок аргументов
❌ менять размеры буферов

---

# 🔒 Важно

Сигнатура функции — это контракт.
Менять её нельзя без согласования.

---

# 🧠 Схема работы

```text
Python/Flet → DLL → C++ API → логика → результат
```

---

# ✅ Итог

Фронт должен:

1. собрать входные данные
2. вызвать `calculate_alarm`
3. проверить код
4. показать результат

Больше ничего не требуется.
