from app.bridges.planner_bridge import (
    make_alarm,
    is_valid_time
)

print(make_alarm(8, 30, 40, 20))

print(is_valid_time(12, 30))
print(is_valid_time(25, 90))