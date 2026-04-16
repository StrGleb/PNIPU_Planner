#pragma once

#ifdef _WIN32
#define ALARM_API __declspec(dllexport)
#else
#define ALARM_API
#endif

extern "C" {

	ALARM_API int calculate_alarm(
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
	);
}
