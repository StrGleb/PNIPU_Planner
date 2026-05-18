from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

ext_modules = [
    Pybind11Extension(
        "planner_algorithm",
        ["cpp/planner_algorithm.cpp"],
    ),
]

setup(
    name="planner_algorithm",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
