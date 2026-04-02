#pragma once

#include "alarm_input.h"
#include "alarm_result.h"

class AlarmService {
public:
    AlarmResult calculate(const AlarmInput& input);
};