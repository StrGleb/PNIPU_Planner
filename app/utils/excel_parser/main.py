"""
excel_path = "2025-2026 Raspisanie ehkzamenov EHTF RIS -25-2b (vesennijj  sessiya).xlsx" -
название таблицы (его не меняем, оставляем тем, что счачано с сайта )
результат в файлах .json
"""

import json
from lib.parser import Parser
from lib.session_parser import SessionParser


def save_json(data: dict, filename: str):
    with open(filename, "w", encoding = "utf-8") as f:
        json.dump(data, f, ensure_ascii = False, indent = 2)

def minutes_to_hhmm(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    return f"{h}:{m:02d}"


def build_normal_json(parser: Parser) -> dict:
    teacher_map = {}
    for a in parser.teacher_location_assignments:
        teacher_map.setdefault(a.staging_id, []).append((a.teacher, a.location))

    odd_lessons = []
    even_lessons = []

    for lesson in parser.lessons:
        p = lesson.insert_params
        assignments = teacher_map.get(p.staging_id, [("", "")])

        for teacher, room in assignments:
            entry = {
                "day": p.day,
                "time_start": minutes_to_hhmm(p.time_start),
                "time_end": minutes_to_hhmm(p.time_end),
                "subject": p.subject,
                "lesson_type": p.category.replace("(", "").replace(")", ""),
                "teacher": "" if teacher == "Unknown" else teacher,
                "room": "" if room == "Unknown" else room
            }

            if p.repeat_rule == 1:
                odd_lessons.append(entry)
            elif p.repeat_rule == 2:
                even_lessons.append(entry)
            else:
                odd_lessons.append(entry)
                even_lessons.append(entry)

    return {
        "version": 1,
        "odd": sorted(odd_lessons, key = lambda x: (x["day"], x["time_start"])),
        "even": sorted(even_lessons, key = lambda x: (x["day"], x["time_start"]))
    }

def build_session_json(parser) -> dict:
    return {
        "version": 1,
        "session": sorted(
            parser.lessons,
            key = lambda x: (x["day"], x["time_start"])
        )
    }

def main():
    excel_path = "2025-2026 Raspisanie ehkzamenov EHTF RIS -25-2b (vesennijj  sessiya).xlsx"

    with open(excel_path, "rb") as f:
        file_bytes = f.read()

    if "sessiya" in excel_path.lower():
        parser = SessionParser()
    else:
        parser = Parser()

    parser.parse_lessons_from_bytes(file_bytes)

    print("Lessons parsed:", len(parser.lessons))

    if isinstance(parser, SessionParser):
        data = build_session_json(parser)
        save_json(data, "timetable_session.json")
        print("JSON file saved: timetable_session.json")

    else:
        data = build_normal_json(parser)
        save_json(data, "timetable.json")
        print("JSON file saved: timetable.json")

if __name__ == "__main__":
    main()