#include "alarm_service.h"

#include <string>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <cmath>

int time_string_to_minutes(const std::string& time_str) {
	if (time_str.size() != 5 || time_str[2] != ':') {
		throw std::invalid_argument("Incorrect time format. Use HH:MM");
	}

	int hours = std::stoi(time_str.substr(0, 2));
	int minutes = std::stoi(time_str.substr(3, 2));

	if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
		throw std::invalid_argument("Incorrect time value");
	}

	return hours * 60 + minutes;
}

std::string minutes_to_time_string(int total_minutes) {
	while (total_minutes < 0) {
		total_minutes += 24 * 60;
	}

	total_minutes %= (24 * 60);

	int hours = total_minutes / 60;
	int minutes = total_minutes % 60;

	std::ostringstream out;
	out << std::setw(2) << std::setfill('0') << hours << ":"
		<< std::setw(2) << std::setfill('0') << minutes;

	return out.str();
}

int minutes_to_day(int alarm_time_minutes) {
	while (alarm_time_minutes < 0)
		alarm_time_minutes = 24 * 60 + alarm_time_minutes;

	if (alarm_time_minutes > 24 * 60)
		alarm_time_minutes = alarm_time_minutes % (24 * 60);

	return alarm_time_minutes;
}

int apply_weather(int final_travel_minutes, double weather_multiplier) {
	double final = final_travel_minutes * weather_multiplier;
	final_travel_minutes = std::ceil(final);

	return final_travel_minutes;
}

int round_down_to_five(int alarm_time_minutes) {
	while (alarm_time_minutes % 5 != 0)
		alarm_time_minutes--;

	return alarm_time_minutes;
}

std::string make_comment(bool use_weather, bool round_to_five) {
	std::string message;

	if (use_weather && round_to_five)
		message = "Weather applied and time rounding.";

	else if (use_weather && !round_to_five)
		message = "Weather applied.";

	else if (!use_weather && round_to_five)
		message = "Time rounding.";

	else message = "No modifiers.";

	return message;
}

AlarmResult AlarmService::calculate(const AlarmInput& input) {

	if (input.travel_minutes < 0 || input.prep_minutes < 0 || input.buffer_minutes < 0)
		throw std::invalid_argument("Entering incorrect data.");

	if (input.weather_multiplier < 1)
		throw std::invalid_argument("Weather coefficient below 1.");

	int event_time_minutes = time_string_to_minutes(input.event_time);

	int final_travel_minutes = input.travel_minutes;
	if (input.use_weather)
		final_travel_minutes = apply_weather(final_travel_minutes, input.weather_multiplier);

	int leave_time_minutes = event_time_minutes - final_travel_minutes;
	int alarm_time_minutes = leave_time_minutes - input.prep_minutes - input.buffer_minutes;

	alarm_time_minutes = minutes_to_day(alarm_time_minutes);
	if (input.round_to_five)
		alarm_time_minutes = round_down_to_five(alarm_time_minutes);


	AlarmResult result;
	result.event_time = input.event_time;
	result.final_travel_minutes = final_travel_minutes;
	result.prep_minutes = input.prep_minutes;
	result.buffer_minutes = input.buffer_minutes;
	result.leave_time = minutes_to_time_string(leave_time_minutes);
	result.alarm_time = minutes_to_time_string(alarm_time_minutes);
	result.weather_applied = input.use_weather;
	result.weather_multiplier = input.weather_multiplier;
	result.rounding_applied = input.round_to_five;
	result.comment = make_comment(input.use_weather, input.round_to_five);
	
	return result;
}