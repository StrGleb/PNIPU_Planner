import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from bridges.planner_bridge import make_alarm

result = make_alarm(
    8,
    30,
    40,
    20
)

print(result)
