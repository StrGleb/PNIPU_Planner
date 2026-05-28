cmake_minimum_required(VERSION 3.20)

project(planner_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(
    PLANNER_NATIVE_OUTPUT_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/bin"
    CACHE PATH
    "Output directory for compiled native libraries"
)
set(
    PLANNER_ANDROID_STL
    "c++"
    CACHE STRING
    "Android STL runtime linked into the shared library"
)

add_library(planner_core SHARED
    src/planner_core.cpp
    src/schedule_parser.cpp
)

target_include_directories(planner_core PRIVATE src)

if(ANDROID)
    find_library(ZLIB_LIBRARY z REQUIRED)
    target_link_libraries(planner_core PRIVATE ${ZLIB_LIBRARY} ${PLANNER_ANDROID_STL})
elseif(MINGW AND EXISTS "C:/msys64/mingw64/include/zlib.h")
    target_include_directories(planner_core PRIVATE "C:/msys64/mingw64/include")
    target_link_libraries(
        planner_core
        PRIVATE
        "C:/msys64/mingw64/lib/libz.a"
        "C:/msys64/mingw64/lib/libwinpthread.a"
    )
    target_link_options(planner_core PRIVATE -static-libgcc -static-libstdc++)

    if(EXISTS "C:/msys64/mingw64/bin/libwinpthread-1.dll")
        add_custom_command(
            TARGET planner_core POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "C:/msys64/mingw64/bin/libwinpthread-1.dll"
                "$<TARGET_FILE_DIR:planner_core>/libwinpthread-1.dll"
        )
    endif()
else()
    find_package(ZLIB REQUIRED)
    target_link_libraries(planner_core PRIVATE ZLIB::ZLIB)
endif()

if(MSVC)
    target_compile_options(planner_core PRIVATE /utf-8)
else()
    target_compile_options(planner_core PRIVATE -finput-charset=UTF-8 -fexec-charset=UTF-8)
endif()

set_target_properties(planner_core PROPERTIES
    OUTPUT_NAME "planner_core"
    RUNTIME_OUTPUT_DIRECTORY "${PLANNER_NATIVE_OUTPUT_DIR}"
    LIBRARY_OUTPUT_DIRECTORY "${PLANNER_NATIVE_OUTPUT_DIR}"
    ARCHIVE_OUTPUT_DIRECTORY "${PLANNER_NATIVE_OUTPUT_DIR}"
)
