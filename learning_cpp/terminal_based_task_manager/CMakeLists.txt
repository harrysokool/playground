cmake_minimum_required(VERSION 3.16)

project(TaskManager)

set(CMAKE_CXX_STANDARD 17)

include(FetchContent)

FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.12.0
)

FetchContent_MakeAvailable(json)

add_executable(
    TaskManager
    src/main.cpp
    src/TaskManager.cpp
)

target_include_directories(
    TaskManager
    PRIVATE include
)

target_link_libraries(
    TaskManager
    PRIVATE nlohmann_json::nlohmann_json
)