#include "alarm_api.h"

#include "../native/alarm/alarm_service.h"
#include "../native/alarm/alarm_input.h"
#include "../native/alarm/alarm_result.h"

#include <cstring>
#include <string>
#include <stdexcept>

static void copy_to_buffer(const std::string& exp, char* imp, int imp_size) {
	if (imp == nullptr || imp_size <= 0)
		return;

	std::strncpy(imp, exp.c_str(), imp_size - 1);
	imp[imp_size - 1] = '\0';
}

int calculate_alarm(
	const char* event_time,
	int travel_minutes,
	int prep_minutes,
	int buffer_minutes,
	bool use_weather,
	double weather_multiplier,
	bool round_to_five,
    char* out_alarm_time,
    int out_alarm_time_size,
    char* out_leave_time,
    int out_leave_time_size,
    char* out_comment,
    int out_comment_size
) {
    try {
        if (event_time == nullptr) {
            return 1;
        }

        AlarmInput input;
        input.event_time = event_time;
        input.travel_minutes = travel_minutes;
        input.prep_minutes = prep_minutes;
        input.buffer_minutes = buffer_minutes;
        input.use_weather = use_weather;
        input.weather_multiplier = weather_multiplier;
        input.round_to_five = round_to_five;

        AlarmService service;
        AlarmResult result = service.calculate(input);

        copy_to_buffer(result.alarm_time, out_alarm_time, out_alarm_time_size);
        copy_to_buffer(result.leave_time, out_leave_time, out_leave_time_size);
        copy_to_buffer(result.comment, out_comment, out_comment_size);

        return 0;
    }
    catch (const std::invalid_argument&) {
        return 2;
    }
    catch (...) {
        return 3;
    }
}


