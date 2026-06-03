#include "planner_core.h"

#include <zlib.h>

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace
{
    struct ZipEntry
    {
        std::string name;
        std::uint16_t compression_method = 0;
        std::uint32_t compressed_size = 0;
        std::uint32_t uncompressed_size = 0;
        std::uint32_t local_header_offset = 0;
    };

    struct CellRef
    {
        int column = 0;
        int row = 0;
    };

    struct MergeRange
    {
        int start_column = 0;
        int start_row = 0;
        int end_column = 0;
        int end_row = 0;

        bool covers(int column, int row) const
        {
            return column >= start_column
                && column <= end_column
                && row >= start_row
                && row <= end_row;
        }
    };

    struct ParsedLesson
    {
        int day = 0;
        std::string date_text;
        std::string time_start;
        std::string time_end;
        std::string subject;
        std::string lesson_type;
        std::string teacher;
        std::string room;
        std::string auditorium;
        std::string building;
    };

    struct ParsedSchedule
    {
        std::string title;
        std::string semester_start;
        std::string schedule_type = "weekly";
        bool first_week_even = false;
        std::vector<ParsedLesson> odd;
        std::vector<ParsedLesson> even;
        std::vector<ParsedLesson> dated;
    };

    std::string g_last_error_message;

    constexpr int kLessonDurationMinutes = 90;
    constexpr int kFirstLessonRow = 4;
    constexpr int kRowsPerDay = 12;
    constexpr int kSlotsPerDay = 6;
    constexpr int kDaysPerWeek = 6;
    constexpr int kLessonColumn = 3; // C
    constexpr int kTimeColumn = 2;   // B

    const std::vector<std::string> kTeacherRoles = {
        "научный руководитель",
        "тренер-преподаватель",
        "профессор",
        "ст. пр.",
        "куратор",
        "доц.",
        "асс.",
        "зав.",
        "преп.",
        "проф.",
        "пр.",
    };

    std::uint16_t read_u16(const std::vector<std::uint8_t>& bytes, std::size_t offset)
    {
        return static_cast<std::uint16_t>(bytes[offset])
            | (static_cast<std::uint16_t>(bytes[offset + 1]) << 8);
    }

    std::uint32_t read_u32(const std::vector<std::uint8_t>& bytes, std::size_t offset)
    {
        return static_cast<std::uint32_t>(bytes[offset])
            | (static_cast<std::uint32_t>(bytes[offset + 1]) << 8)
            | (static_cast<std::uint32_t>(bytes[offset + 2]) << 16)
            | (static_cast<std::uint32_t>(bytes[offset + 3]) << 24);
    }

    std::vector<std::uint8_t> read_file_bytes(const char* path)
    {
        std::ifstream stream(path, std::ios::binary);
        if (!stream) {
            throw std::runtime_error("Не удалось открыть xlsx-файл.");
        }

        stream.seekg(0, std::ios::end);
        const std::streamoff length = stream.tellg();
        stream.seekg(0, std::ios::beg);

        if (length <= 0) {
            throw std::runtime_error("XLSX-файл пустой.");
        }

        std::vector<std::uint8_t> bytes(static_cast<std::size_t>(length));
        stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
        if (!stream) {
            throw std::runtime_error("Не удалось прочитать xlsx-файл.");
        }

        return bytes;
    }

    std::vector<ZipEntry> read_zip_directory(const std::vector<std::uint8_t>& bytes)
    {
        const std::uint32_t eocd_signature = 0x06054b50;
        const std::uint32_t central_signature = 0x02014b50;

        if (bytes.size() < 22) {
            throw std::runtime_error("Некорректный XLSX: слишком короткий ZIP.");
        }

        std::size_t eocd_offset = std::string::npos;
        const std::size_t search_start = bytes.size() > (22 + 0xFFFF)
            ? bytes.size() - (22 + 0xFFFF)
            : 0;

        for (std::size_t index = bytes.size() - 22; ; --index) {
            if (read_u32(bytes, index) == eocd_signature) {
                eocd_offset = index;
                break;
            }
            if (index == search_start) {
                break;
            }
        }

        if (eocd_offset == std::string::npos) {
            throw std::runtime_error("Некорректный XLSX: не найден ZIP directory.");
        }

        const std::uint16_t entries_count = read_u16(bytes, eocd_offset + 10);
        const std::uint32_t directory_size = read_u32(bytes, eocd_offset + 12);
        const std::uint32_t directory_offset = read_u32(bytes, eocd_offset + 16);

        if (directory_offset + directory_size > bytes.size()) {
            throw std::runtime_error("Некорректный XLSX: central directory выходит за границы файла.");
        }

        std::vector<ZipEntry> entries;
        entries.reserve(entries_count);

        std::size_t cursor = directory_offset;
        for (std::uint16_t i = 0; i < entries_count; ++i) {
            if (cursor + 46 > bytes.size() || read_u32(bytes, cursor) != central_signature) {
                throw std::runtime_error("Некорректный XLSX: повреждена central directory.");
            }

            const std::uint16_t file_name_length = read_u16(bytes, cursor + 28);
            const std::uint16_t extra_length = read_u16(bytes, cursor + 30);
            const std::uint16_t comment_length = read_u16(bytes, cursor + 32);

            ZipEntry entry;
            entry.compression_method = read_u16(bytes, cursor + 10);
            entry.compressed_size = read_u32(bytes, cursor + 20);
            entry.uncompressed_size = read_u32(bytes, cursor + 24);
            entry.local_header_offset = read_u32(bytes, cursor + 42);
            entry.name.assign(
                reinterpret_cast<const char*>(bytes.data() + cursor + 46),
                file_name_length
            );

            entries.push_back(entry);
            cursor += 46 + file_name_length + extra_length + comment_length;
        }

        return entries;
    }

    std::string inflate_zip_entry(
        const std::vector<std::uint8_t>& bytes,
        const ZipEntry& entry
    )
    {
        const std::uint32_t local_signature = 0x04034b50;
        const std::size_t offset = entry.local_header_offset;

        if (offset + 30 > bytes.size() || read_u32(bytes, offset) != local_signature) {
            throw std::runtime_error("Некорректный XLSX: local header не найден.");
        }

        const std::uint16_t file_name_length = read_u16(bytes, offset + 26);
        const std::uint16_t extra_length = read_u16(bytes, offset + 28);
        const std::size_t data_offset = offset + 30 + file_name_length + extra_length;

        if (data_offset + entry.compressed_size > bytes.size()) {
            throw std::runtime_error("Некорректный XLSX: данные ZIP entry повреждены.");
        }

        const unsigned char* source = bytes.data() + data_offset;

        if (entry.compression_method == 0) {
            return std::string(
                reinterpret_cast<const char*>(source),
                reinterpret_cast<const char*>(source + entry.uncompressed_size)
            );
        }

        if (entry.compression_method != 8) {
            throw std::runtime_error("Неподдерживаемый метод сжатия XLSX.");
        }

        std::string output(entry.uncompressed_size, '\0');
        z_stream stream {};
        stream.next_in = const_cast<Bytef*>(reinterpret_cast<const Bytef*>(source));
        stream.avail_in = entry.compressed_size;
        stream.next_out = reinterpret_cast<Bytef*>(output.data());
        stream.avail_out = entry.uncompressed_size;

        if (inflateInit2(&stream, -MAX_WBITS) != Z_OK) {
            throw std::runtime_error("Не удалось инициализировать zlib для XLSX.");
        }

        const int result = inflate(&stream, Z_FINISH);
        inflateEnd(&stream);

        if (result != Z_STREAM_END) {
            throw std::runtime_error("Не удалось распаковать XML из XLSX.");
        }

        output.resize(stream.total_out);
        return output;
    }

    std::string read_zip_text_file(
        const std::vector<std::uint8_t>& bytes,
        const std::vector<ZipEntry>& entries,
        const std::string& file_name
    )
    {
        for (const ZipEntry& entry : entries) {
            if (entry.name == file_name) {
                return inflate_zip_entry(bytes, entry);
            }
        }

        throw std::runtime_error("В XLSX не найден обязательный XML-файл: " + file_name);
    }

    void replace_all(std::string& text, const std::string& from, const std::string& to)
    {
        if (from.empty()) {
            return;
        }

        std::size_t position = 0;
        while ((position = text.find(from, position)) != std::string::npos) {
            text.replace(position, from.size(), to);
            position += to.size();
        }
    }

    std::string decode_xml_entities(std::string text)
    {
        replace_all(text, "&amp;", "&");
        replace_all(text, "&lt;", "<");
        replace_all(text, "&gt;", ">");
        replace_all(text, "&quot;", "\"");
        replace_all(text, "&apos;", "'");
        return text;
    }

    std::string trim_ascii(std::string text)
    {
        replace_all(text, "\xC2\xA0", " ");
        const auto is_trim_char = [](unsigned char ch) {
            return std::isspace(ch) != 0;
        };

        while (!text.empty() && is_trim_char(static_cast<unsigned char>(text.front()))) {
            text.erase(text.begin());
        }
        while (!text.empty() && is_trim_char(static_cast<unsigned char>(text.back()))) {
            text.pop_back();
        }

        return text;
    }

    std::string collapse_spaces(const std::string& text)
    {
        std::string normalized = text;
        replace_all(normalized, "\xC2\xA0", " ");
        replace_all(normalized, "\r", "\n");

        std::string result;
        result.reserve(normalized.size());

        bool previous_space = false;
        for (unsigned char ch : normalized) {
            if (ch == '\n' || ch == '\t' || ch == ' ') {
                if (!previous_space) {
                    result.push_back(' ');
                    previous_space = true;
                }
            }
            else {
                result.push_back(static_cast<char>(ch));
                previous_space = false;
            }
        }

        return trim_ascii(result);
    }

    std::vector<std::string> split_lines(const std::string& text)
    {
        std::string normalized = text;
        replace_all(normalized, "\r\n", "\n");
        replace_all(normalized, "\r", "\n");
        replace_all(normalized, "\xC2\xA0", " ");

        std::vector<std::string> lines;
        std::stringstream stream(normalized);
        std::string line;
        while (std::getline(stream, line, '\n')) {
            line = trim_ascii(line);
            if (!line.empty()) {
                lines.push_back(line);
            }
        }
        return lines;
    }

    std::string join_strings(const std::vector<std::string>& values, const std::string& separator)
    {
        std::string result;
        for (std::size_t index = 0; index < values.size(); ++index) {
            if (index != 0) {
                result += separator;
            }
            result += values[index];
        }
        return result;
    }

    std::string json_escape(const std::string& text)
    {
        std::string escaped;
        escaped.reserve(text.size() + 16);

        for (unsigned char ch : text) {
            switch (ch) {
                case '\\': escaped += "\\\\"; break;
                case '"': escaped += "\\\""; break;
                case '\b': escaped += "\\b"; break;
                case '\f': escaped += "\\f"; break;
                case '\n': escaped += "\\n"; break;
                case '\r': escaped += "\\r"; break;
                case '\t': escaped += "\\t"; break;
                default:
                    if (ch < 0x20) {
                        char buffer[7] {};
                        std::snprintf(buffer, sizeof(buffer), "\\u%04x", ch);
                        escaped += buffer;
                    }
                    else {
                        escaped.push_back(static_cast<char>(ch));
                    }
                    break;
            }
        }

        return escaped;
    }

    int month_from_russian_name(const std::string& month_name)
    {
        static const std::map<std::string, int> months = {
            {"января", 1},
            {"февраля", 2},
            {"марта", 3},
            {"апреля", 4},
            {"мая", 5},
            {"июня", 6},
            {"июля", 7},
            {"августа", 8},
            {"сентября", 9},
            {"октября", 10},
            {"ноября", 11},
            {"декабря", 12},
        };

        const auto found = months.find(month_name);
        return found == months.end() ? 0 : found->second;
    }

    std::string format_date(int day, int month, int year)
    {
        char buffer[16] {};
        std::snprintf(buffer, sizeof(buffer), "%02d.%02d.%04d", day, month, year);
        return buffer;
    }

    std::string format_time_from_minutes(int minutes)
    {
        const int hours = minutes / 60;
        const int mins = minutes % 60;
        char buffer[8] {};
        std::snprintf(buffer, sizeof(buffer), "%d:%02d", hours, mins);
        return buffer;
    }

    int parse_time_to_minutes(const std::string& value)
    {
        const std::string trimmed = trim_ascii(value);
        const std::size_t colon = trimmed.find(':');
        if (colon == std::string::npos) {
            return -1;
        }

        try {
            const int hours = std::stoi(trimmed.substr(0, colon));
            const int minutes = std::stoi(trimmed.substr(colon + 1));
            if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
                return -1;
            }
            return hours * 60 + minutes;
        }
        catch (...) {
            return -1;
        }
    }

    CellRef parse_cell_ref(const std::string& ref)
    {
        CellRef result;
        std::size_t index = 0;

        while (index < ref.size() && std::isalpha(static_cast<unsigned char>(ref[index]))) {
            result.column = result.column * 26 + (std::toupper(static_cast<unsigned char>(ref[index])) - 'A' + 1);
            ++index;
        }

        if (index == 0 || index >= ref.size()) {
            throw std::runtime_error("Некорректная ссылка на ячейку в XLSX.");
        }

        result.row = std::stoi(ref.substr(index));
        return result;
    }

    std::string cell_ref_name(int column, int row)
    {
        std::string column_name;
        int current = column;
        while (current > 0) {
            const int remainder = (current - 1) % 26;
            column_name.insert(column_name.begin(), static_cast<char>('A' + remainder));
            current = (current - 1) / 26;
        }
        return column_name + std::to_string(row);
    }

    std::vector<std::string> parse_shared_strings(const std::string& xml)
    {
        std::vector<std::string> values;
        std::size_t position = 0;

        while ((position = xml.find("<x:si", position)) != std::string::npos) {
            const std::size_t start = xml.find('>', position);
            const std::size_t end = xml.find("</x:si>", start);
            if (start == std::string::npos || end == std::string::npos) {
                break;
            }

            std::string item_xml = xml.substr(start + 1, end - start - 1);
            std::string value;

            std::size_t text_position = 0;
            while ((text_position = item_xml.find("<x:t", text_position)) != std::string::npos) {
                const std::size_t tag_end = item_xml.find('>', text_position);
                const std::size_t text_end = item_xml.find("</x:t>", tag_end);
                if (tag_end == std::string::npos || text_end == std::string::npos) {
                    break;
                }

                value += decode_xml_entities(item_xml.substr(tag_end + 1, text_end - tag_end - 1));
                text_position = text_end + 6;
            }

            values.push_back(value);
            position = end + 7;
        }

        return values;
    }

    std::unordered_map<std::string, std::string> parse_cells(
        const std::string& xml,
        const std::vector<std::string>& shared_strings
    )
    {
        std::unordered_map<std::string, std::string> cells;
        std::size_t position = 0;

        while ((position = xml.find("<x:c ", position)) != std::string::npos) {
            const std::size_t tag_end = xml.find('>', position);
            if (tag_end == std::string::npos) {
                break;
            }

            const bool self_closing = tag_end > position && xml[tag_end - 1] == '/';
            const std::string tag = xml.substr(position, tag_end - position + 1);

            const std::size_t ref_pos = tag.find(" r=\"");
            if (ref_pos == std::string::npos) {
                position = tag_end + 1;
                continue;
            }

            const std::size_t ref_start = ref_pos + 4;
            const std::size_t ref_end = tag.find('"', ref_start);
            if (ref_end == std::string::npos) {
                position = tag_end + 1;
                continue;
            }

            std::string cell_name = tag.substr(ref_start, ref_end - ref_start);
            std::string cell_type;

            const std::size_t type_pos = tag.find(" t=\"");
            if (type_pos != std::string::npos) {
                const std::size_t type_start = type_pos + 4;
                const std::size_t type_end = tag.find('"', type_start);
                if (type_end != std::string::npos) {
                    cell_type = tag.substr(type_start, type_end - type_start);
                }
            }

            std::string value;
            if (!self_closing) {
                const std::size_t close_pos = xml.find("</x:c>", tag_end);
                if (close_pos == std::string::npos) {
                    break;
                }

                const std::string body = xml.substr(tag_end + 1, close_pos - tag_end - 1);
                const std::size_t value_start = body.find("<x:v>");
                if (value_start != std::string::npos) {
                    const std::size_t value_end = body.find("</x:v>", value_start);
                    if (value_end != std::string::npos) {
                        value = body.substr(value_start + 5, value_end - value_start - 5);
                    }
                }
                else {
                    const std::size_t text_start = body.find("<x:t");
                    if (text_start != std::string::npos) {
                        const std::size_t text_tag_end = body.find('>', text_start);
                        const std::size_t text_end = body.find("</x:t>", text_tag_end);
                        if (text_tag_end != std::string::npos && text_end != std::string::npos) {
                            value = body.substr(text_tag_end + 1, text_end - text_tag_end - 1);
                        }
                    }
                }

                position = close_pos + 6;
            }
            else {
                position = tag_end + 1;
            }

            if (cell_type == "s" && !value.empty()) {
                const int shared_index = std::stoi(value);
                if (shared_index >= 0 && static_cast<std::size_t>(shared_index) < shared_strings.size()) {
                    cells[cell_name] = shared_strings[static_cast<std::size_t>(shared_index)];
                }
            }
            else if (!value.empty()) {
                cells[cell_name] = decode_xml_entities(value);
            }
        }

        return cells;
    }

    std::vector<MergeRange> parse_merge_ranges(const std::string& xml)
    {
        std::vector<MergeRange> ranges;
        std::size_t position = 0;

        while ((position = xml.find("<x:mergeCell", position)) != std::string::npos) {
            const std::size_t ref_pos = xml.find(" ref=\"", position);
            if (ref_pos == std::string::npos) {
                break;
            }

            const std::size_t ref_start = ref_pos + 6;
            const std::size_t ref_end = xml.find('"', ref_start);
            if (ref_end == std::string::npos) {
                break;
            }

            const std::string ref = xml.substr(ref_start, ref_end - ref_start);
            const std::size_t colon = ref.find(':');

            MergeRange range;
            if (colon == std::string::npos) {
                CellRef cell = parse_cell_ref(ref);
                range.start_column = cell.column;
                range.end_column = cell.column;
                range.start_row = cell.row;
                range.end_row = cell.row;
            }
            else {
                CellRef start = parse_cell_ref(ref.substr(0, colon));
                CellRef end = parse_cell_ref(ref.substr(colon + 1));
                range.start_column = start.column;
                range.start_row = start.row;
                range.end_column = end.column;
                range.end_row = end.row;
            }

            ranges.push_back(range);
            position = ref_end + 1;
        }

        return ranges;
    }

    const MergeRange* find_covering_merge(
        const std::vector<MergeRange>& ranges,
        int column,
        int row
    )
    {
        for (const MergeRange& range : ranges) {
            if (range.covers(column, row)) {
                return &range;
            }
        }
        return nullptr;
    }

    bool starts_with_time_prefix(const std::string& text)
    {
        return text.size() >= 6
            && std::isdigit(static_cast<unsigned char>(text[0])) != 0
            && std::isdigit(static_cast<unsigned char>(text[2])) != 0
            && text[1] == ':'
            && text[4] == ' ';
    }

    std::size_t find_type_marker(const std::string& text, std::string* type_value)
    {
        static const std::vector<std::string> markers = {
            "(лек)",
            "(пр)",
            "(лаб)",
            "(кср)",
        };

        for (const std::string& marker : markers) {
            const std::size_t pos = text.find(marker);
            if (pos != std::string::npos) {
                if (type_value != nullptr) {
                    *type_value = marker.substr(1, marker.size() - 2);
                }
                return pos;
            }
        }

        return std::string::npos;
    }

    std::size_t find_next_teacher_role(const std::string& text, std::size_t start)
    {
        std::size_t best = std::string::npos;
        for (const std::string& role : kTeacherRoles) {
            const std::size_t current = text.find(role, start);
            if (current != std::string::npos && (best == std::string::npos || current < best)) {
                best = current;
            }
        }
        return best;
    }

    std::pair<std::vector<std::string>, std::vector<std::string>> parse_teacher_room_lists(const std::string& text)
    {
        std::vector<std::string> teachers;
        std::vector<std::string> rooms;

        std::size_t current = find_next_teacher_role(text, 0);
        if (current == std::string::npos) {
            return {teachers, rooms};
        }

        while (current != std::string::npos) {
            std::size_t next = find_next_teacher_role(text, current + 1);
            std::string segment = trim_ascii(text.substr(current, next == std::string::npos ? std::string::npos : next - current));

            std::size_t room_start = std::string::npos;
            for (std::size_t index = 0; index < segment.size(); ++index) {
                if (std::isdigit(static_cast<unsigned char>(segment[index])) != 0) {
                    room_start = index;
                    break;
                }
            }

            std::string teacher = room_start == std::string::npos
                ? trim_ascii(segment)
                : trim_ascii(segment.substr(0, room_start));
            std::string room = room_start == std::string::npos
                ? std::string()
                : trim_ascii(segment.substr(room_start));

            if (!teacher.empty() && std::find(teachers.begin(), teachers.end(), teacher) == teachers.end()) {
                teachers.push_back(teacher);
            }
            if (!room.empty() && std::find(rooms.begin(), rooms.end(), room) == rooms.end()) {
                rooms.push_back(room);
            }

            current = next;
        }

        return {teachers, rooms};
    }

    std::pair<std::string, std::string> split_room_parts(const std::string& room)
    {
        const std::string trimmed = trim_ascii(room);
        if (trimmed.empty()) {
            return {"", ""};
        }

        const std::size_t space = trimmed.find(' ');
        if (space == std::string::npos) {
            return {trimmed, ""};
        }

        return {
            trim_ascii(trimmed.substr(0, space)),
            trim_ascii(trimmed.substr(space + 1)),
        };
    }

    int days_from_civil(int year, int month, int day)
    {
        year -= month <= 2;
        const int era = (year >= 0 ? year : year - 399) / 400;
        const unsigned yoe = static_cast<unsigned>(year - era * 400);
        const unsigned doy = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5
            + static_cast<unsigned>(day) - 1;
        const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
        return era * 146097 + static_cast<int>(doe) - 719468;
    }

    int iso_weekday_from_date(int day, int month, int year)
    {
        const int absolute_days = days_from_civil(year, month, day);
        const int weekday_base = (absolute_days + 3) % 7;
        return weekday_base >= 0 ? weekday_base + 1 : weekday_base + 8;
    }

    std::string get_required_cell(
        const std::unordered_map<std::string, std::string>& cells,
        const std::string& cell_name
    );

    bool looks_like_session_sheet(const std::unordered_map<std::string, std::string>& cells)
    {
        const auto header_a = cells.find("A3");
        const auto header_b = cells.find("B3");
        if (header_a == cells.end() || header_b == cells.end()) {
            return false;
        }

        return collapse_spaces(header_a->second) == "Дни"
            && collapse_spaces(header_b->second) == "Числа";
    }

    std::tuple<int, int, int> parse_session_date(
        const std::string& raw_value,
        int year_a,
        int year_b
    )
    {
        const std::string value = collapse_spaces(raw_value);
        const std::size_t dot = value.find('.');
        if (dot == std::string::npos) {
            throw std::runtime_error("Не удалось прочитать дату пары из файла сессии.");
        }

        const int day = std::stoi(value.substr(0, dot));
        const int month = std::stoi(value.substr(dot + 1, 2));
        const int year = month >= 8 ? year_a : year_b;
        return {day, month, year};
    }

    std::size_t find_first_teacher_role(const std::string& text, std::size_t start = 0)
    {
        std::size_t best = std::string::npos;
        for (const std::string& role : kTeacherRoles) {
            const std::size_t current = text.find(role, start);
            if (current != std::string::npos && (best == std::string::npos || current < best)) {
                best = current;
            }
        }
        return best;
    }

    ParsedLesson parse_session_text(
        int day,
        int month,
        int year,
        const std::string& raw_text
    )
    {
        const std::vector<std::string> lines = split_lines(raw_text);
        if (lines.empty()) {
            throw std::runtime_error("В файле сессии встретилась пустая ячейка пары.");
        }

        const std::string first_line = lines.front();
        const std::size_t space = first_line.find(' ');
        if (space == std::string::npos) {
            throw std::runtime_error("В файле сессии не удалось прочитать время пары.");
        }

        const std::string time_start = trim_ascii(first_line.substr(0, space));
        const int start_minutes = parse_time_to_minutes(time_start);
        if (start_minutes < 0) {
            throw std::runtime_error("В файле сессии найдено некорректное время пары.");
        }

        std::vector<std::string> payload_lines;
        payload_lines.push_back(trim_ascii(first_line.substr(space + 1)));
        for (std::size_t index = 1; index < lines.size(); ++index) {
            payload_lines.push_back(lines[index]);
        }

        const std::string payload = collapse_spaces(join_strings(payload_lines, " "));
        if (payload.empty()) {
            throw std::runtime_error("В файле сессии не найдено название пары.");
        }

        std::string subject = payload;
        std::string teacher;
        std::string room;
        std::string auditorium;
        std::string building;

        const std::size_t teacher_pos = find_first_teacher_role(payload);
        if (teacher_pos != std::string::npos) {
            subject = trim_ascii(payload.substr(0, teacher_pos));
            const auto [teachers, rooms] = parse_teacher_room_lists(payload.substr(teacher_pos));
            teacher = join_strings(teachers, " / ");
            room = join_strings(rooms, " / ");
            const auto [aud, build] = split_room_parts(rooms.empty() ? std::string() : rooms.front());
            auditorium = aud;
            building = build;
        }
        else {
            std::size_t room_pos = std::string::npos;
            for (std::size_t index = 0; index < payload.size(); ++index) {
                if (std::isdigit(static_cast<unsigned char>(payload[index])) != 0) {
                    room_pos = index;
                    break;
                }
            }

            if (room_pos != std::string::npos) {
                subject = trim_ascii(payload.substr(0, room_pos));
                room = trim_ascii(payload.substr(room_pos));
                const auto [aud, build] = split_room_parts(room);
                auditorium = aud;
                building = build;
            }
        }

        ParsedLesson lesson;
        lesson.day = iso_weekday_from_date(day, month, year);
        lesson.date_text = format_date(day, month, year);
        lesson.time_start = time_start;
        lesson.time_end = format_time_from_minutes(start_minutes + kLessonDurationMinutes);
        lesson.subject = subject;
        lesson.teacher = teacher;
        lesson.room = room;
        lesson.auditorium = auditorium;
        lesson.building = building;
        return lesson;
    }

    ParsedSchedule parse_session_schedule(
        const std::unordered_map<std::string, std::string>& cells
    )
    {
        ParsedSchedule schedule;
        schedule.title = trim_ascii(get_required_cell(cells, "A1"));
        schedule.schedule_type = "session";

        int year_a = 0;
        int year_b = 0;
        {
            const std::string years_info = collapse_spaces(schedule.title);
            std::size_t first_digit = years_info.find_first_of("0123456789");
            if (first_digit == std::string::npos || first_digit + 9 >= years_info.size()) {
                throw std::runtime_error("Не удалось определить учебный год из заголовка файла сессии.");
            }
            year_a = std::stoi(years_info.substr(first_digit, 4));
            std::size_t second_digit = years_info.find_first_of("0123456789", first_digit + 4);
            if (second_digit == std::string::npos) {
                throw std::runtime_error("Не удалось определить второй год из заголовка файла сессии.");
            }
            year_b = std::stoi(years_info.substr(second_digit, 4));
        }

        for (int row = 4; row <= 128; ++row) {
            const std::string event_cell = cell_ref_name(3, row);
            const auto event_found = cells.find(event_cell);
            if (event_found == cells.end() || trim_ascii(event_found->second).empty()) {
                continue;
            }

            const std::string date_cell = cell_ref_name(2, row);
            const auto date_found = cells.find(date_cell);
            if (date_found == cells.end()) {
                continue;
            }

            const auto [day, month, year] = parse_session_date(date_found->second, year_a, year_b);
            schedule.dated.push_back(parse_session_text(day, month, year, event_found->second));
        }

        if (schedule.dated.empty()) {
            throw std::runtime_error("В файле сессии не найдено ни одной пары.");
        }

        std::sort(schedule.dated.begin(), schedule.dated.end(), [](const ParsedLesson& lhs, const ParsedLesson& rhs) {
            if (lhs.date_text != rhs.date_text) {
                const int lhs_day = std::stoi(lhs.date_text.substr(0, 2));
                const int lhs_month = std::stoi(lhs.date_text.substr(3, 2));
                const int lhs_year = std::stoi(lhs.date_text.substr(6, 4));
                const int rhs_day = std::stoi(rhs.date_text.substr(0, 2));
                const int rhs_month = std::stoi(rhs.date_text.substr(3, 2));
                const int rhs_year = std::stoi(rhs.date_text.substr(6, 4));
                return days_from_civil(lhs_year, lhs_month, lhs_day)
                    < days_from_civil(rhs_year, rhs_month, rhs_day);
            }
            const int lhs_minutes = parse_time_to_minutes(lhs.time_start);
            const int rhs_minutes = parse_time_to_minutes(rhs.time_start);
            if (lhs_minutes != rhs_minutes) {
                return lhs_minutes < rhs_minutes;
            }
            return lhs.subject < rhs.subject;
        });
        schedule.semester_start = schedule.dated.front().date_text;
        schedule.first_week_even = false;
        return schedule;
    }

    ParsedLesson parse_lesson_text(int day, const std::string& time_start, const std::string& raw_text)
    {
        const int start_minutes = parse_time_to_minutes(time_start);
        if (start_minutes < 0) {
            throw std::runtime_error("В XLSX встретилось некорректное время пары.");
        }

        const int end_minutes = start_minutes + kLessonDurationMinutes;
        const std::string flattened = collapse_spaces(raw_text);
        if (flattened.empty()) {
            throw std::runtime_error("В XLSX встретилась пустая ячейка пары.");
        }

        std::string lesson_type;
        std::size_t type_position = find_type_marker(flattened, &lesson_type);

        std::string subject;
        std::string tail;

        if (type_position == std::string::npos) {
            subject = flattened;
        }
        else {
            subject = trim_ascii(flattened.substr(0, type_position));
            tail = trim_ascii(flattened.substr(type_position + lesson_type.size() + 2));
        }

        if (starts_with_time_prefix(subject)) {
            subject = trim_ascii(subject.substr(5));
        }

        const auto [teachers, rooms] = parse_teacher_room_lists(tail);
        const std::string teacher = join_strings(teachers, " / ");
        const std::string room = join_strings(rooms, " / ");

        const auto [auditorium, building] = split_room_parts(rooms.empty() ? std::string() : rooms.front());

        ParsedLesson lesson;
        lesson.day = day;
        lesson.time_start = time_start;
        lesson.time_end = format_time_from_minutes(end_minutes);
        lesson.subject = subject;
        lesson.lesson_type = lesson_type;
        lesson.teacher = teacher;
        lesson.room = room;
        lesson.auditorium = auditorium;
        lesson.building = building;
        return lesson;
    }

    std::string get_required_cell(
        const std::unordered_map<std::string, std::string>& cells,
        const std::string& cell_name
    )
    {
        const auto found = cells.find(cell_name);
        if (found == cells.end()) {
            throw std::runtime_error("В XLSX не найдена обязательная ячейка " + cell_name);
        }
        return found->second;
    }

    ParsedSchedule parse_schedule(const char* xlsx_path)
    {
        const std::vector<std::uint8_t> zip_bytes = read_file_bytes(xlsx_path);
        const std::vector<ZipEntry> entries = read_zip_directory(zip_bytes);

        const std::string shared_strings_xml = read_zip_text_file(zip_bytes, entries, "xl/sharedStrings.xml");
        const std::string sheet_xml = read_zip_text_file(zip_bytes, entries, "xl/worksheets/sheet1.xml");

        const std::vector<std::string> shared_strings = parse_shared_strings(shared_strings_xml);
        const std::unordered_map<std::string, std::string> cells = parse_cells(sheet_xml, shared_strings);
        const std::vector<MergeRange> merges = parse_merge_ranges(sheet_xml);

        if (looks_like_session_sheet(cells)) {
            return parse_session_schedule(cells);
        }

        ParsedSchedule schedule;
        schedule.title = trim_ascii(get_required_cell(cells, "A1"));

        const std::string start_info = collapse_spaces(get_required_cell(cells, "A2"));
        const std::string years_info = collapse_spaces(schedule.title);

        int year_a = 0;
        int year_b = 0;
        {
            std::size_t first_digit = years_info.find_first_of("0123456789");
            if (first_digit == std::string::npos || first_digit + 9 >= years_info.size()) {
                throw std::runtime_error("Не удалось определить учебный год из заголовка XLSX.");
            }
            year_a = std::stoi(years_info.substr(first_digit, 4));
            std::size_t second_digit = years_info.find_first_of("0123456789", first_digit + 4);
            if (second_digit == std::string::npos) {
                throw std::runtime_error("Не удалось определить второй год из заголовка XLSX.");
            }
            year_b = std::stoi(years_info.substr(second_digit, 4));
        }

        {
            const std::string marker = "Начало занятий с ";
            const std::size_t start_pos = start_info.find(marker);
            const std::size_t week_pos = start_info.find(" неделя");
            if (start_pos == std::string::npos || week_pos == std::string::npos) {
                throw std::runtime_error("Не удалось прочитать строку начала занятий из XLSX.");
            }

            const std::size_t payload_start = start_pos + marker.size();
            const std::size_t dash_pos = start_info.find(" - ", payload_start);
            if (dash_pos == std::string::npos || dash_pos >= week_pos) {
                throw std::runtime_error("Строка начала занятий имеет неожиданный формат.");
            }

            const std::string date_part = trim_ascii(start_info.substr(payload_start, dash_pos - payload_start));
            const std::string week_part = trim_ascii(start_info.substr(dash_pos + 3, week_pos - (dash_pos + 3)));

            std::stringstream date_stream(date_part);
            int day = 0;
            std::string month_name;
            date_stream >> day >> month_name;

            const int month = month_from_russian_name(month_name);
            if (day <= 0 || month == 0) {
                throw std::runtime_error("Не удалось определить дату начала занятий из XLSX.");
            }

            const int year = month >= 8 ? year_a : year_b;
            schedule.semester_start = format_date(day, month, year);
            schedule.first_week_even = week_part == "2";
        }

        for (int day_index = 0; day_index < kDaysPerWeek; ++day_index) {
            const int day = day_index + 1;
            const int day_start_row = kFirstLessonRow + day_index * kRowsPerDay;

            for (int slot_index = 0; slot_index < kSlotsPerDay; ++slot_index) {
                const int top_row = day_start_row + slot_index * 2;
                const int bottom_row = top_row + 1;
                const std::string time_start = trim_ascii(get_required_cell(cells, cell_ref_name(kTimeColumn, top_row)));

                const std::string top_cell_name = cell_ref_name(kLessonColumn, top_row);
                const std::string bottom_cell_name = cell_ref_name(kLessonColumn, bottom_row);

                const std::string top_text = cells.count(top_cell_name) ? cells.at(top_cell_name) : "";
                const std::string bottom_text = cells.count(bottom_cell_name) ? cells.at(bottom_cell_name) : "";

                const MergeRange* merge = find_covering_merge(merges, kLessonColumn, top_row);
                const bool shared_for_both_weeks =
                    merge != nullptr
                    && merge->start_column == kLessonColumn
                    && merge->end_column >= 4
                    && merge->start_row == top_row
                    && merge->end_row == bottom_row;

                if (shared_for_both_weeks) {
                    if (!trim_ascii(top_text).empty()) {
                        ParsedLesson lesson = parse_lesson_text(day, time_start, top_text);
                        schedule.odd.push_back(lesson);
                        schedule.even.push_back(lesson);
                    }
                    continue;
                }

                if (!trim_ascii(top_text).empty()) {
                    schedule.odd.push_back(parse_lesson_text(day, time_start, top_text));
                }

                if (!trim_ascii(bottom_text).empty()) {
                    schedule.even.push_back(parse_lesson_text(day, time_start, bottom_text));
                }
            }
        }

        return schedule;
    }

    void write_schedule_json(const ParsedSchedule& schedule, const char* output_json_path)
    {
        std::ofstream stream(output_json_path, std::ios::binary);
        if (!stream) {
            throw std::runtime_error("Не удалось открыть файл назначения для schedule.json.");
        }

        auto write_lessons = [&stream](const std::vector<ParsedLesson>& lessons) {
            for (std::size_t index = 0; index < lessons.size(); ++index) {
                const ParsedLesson& lesson = lessons[index];
                stream
                    << "    {\n"
                    << "      \"day\": " << lesson.day << ",\n"
                    << "      \"date_text\": \"" << json_escape(lesson.date_text) << "\",\n"
                    << "      \"time_start\": \"" << json_escape(lesson.time_start) << "\",\n"
                    << "      \"time_end\": \"" << json_escape(lesson.time_end) << "\",\n"
                    << "      \"subject\": \"" << json_escape(lesson.subject) << "\",\n"
                    << "      \"lesson_type\": \"" << json_escape(lesson.lesson_type) << "\",\n"
                    << "      \"teacher\": \"" << json_escape(lesson.teacher) << "\",\n"
                    << "      \"room\": \"" << json_escape(lesson.room) << "\",\n"
                    << "      \"auditorium\": \"" << json_escape(lesson.auditorium) << "\",\n"
                    << "      \"building\": \"" << json_escape(lesson.building) << "\"\n"
                    << "    }";

                if (index + 1 != lessons.size()) {
                    stream << ",";
                }
                stream << "\n";
            }
        };

        stream
            << "{\n"
            << "  \"version\": 3,\n"
            << "  \"title\": \"" << json_escape(schedule.title) << "\",\n"
            << "  \"semester_start\": \"" << json_escape(schedule.semester_start) << "\",\n"
            << "  \"first_week_even\": " << (schedule.first_week_even ? "true" : "false") << ",\n"
            << "  \"schedule_type\": \"" << json_escape(schedule.schedule_type) << "\",\n"
            << "  \"odd\": [\n";
        write_lessons(schedule.odd);
        stream
            << "  ],\n"
            << "  \"even\": [\n";
        write_lessons(schedule.even);
        stream
            << "  ],\n"
            << "  \"dated\": [\n";
        write_lessons(schedule.dated);
        stream
            << "  ]\n"
            << "}\n";
    }
}

int parse_schedule_xlsx(const char* xlsx_path, const char* output_json_path)
{
    try {
        if (xlsx_path == nullptr || output_json_path == nullptr) {
            throw std::runtime_error("Не передан путь к XLSX или к schedule.json.");
        }

        const ParsedSchedule schedule = parse_schedule(xlsx_path);
        write_schedule_json(schedule, output_json_path);
        g_last_error_message.clear();
        return 1;
    }
    catch (const std::exception& error) {
        g_last_error_message = error.what();
        return 0;
    }
    catch (...) {
        g_last_error_message = "Неизвестная ошибка native-парсера XLSX.";
        return 0;
    }
}

int copy_last_error_message(char* buffer, int capacity)
{
    if (buffer == nullptr || capacity <= 0) {
        return 0;
    }

    const int size = static_cast<int>(std::min<std::size_t>(
        g_last_error_message.size(),
        static_cast<std::size_t>(capacity - 1)
    ));
    std::memcpy(buffer, g_last_error_message.data(), size);
    buffer[size] = '\0';
    return size;
}
