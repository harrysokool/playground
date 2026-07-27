cmake_minimum_required(VERSION 3.16)

project(TaskManager)

set(CMAKE_CXX_STANDARD 17)

add_executable(
    TaskManager
    src/main.cpp
    src/TaskManager.cpp
)

target_include_directories(
    TaskManager
    PRIVATE include
)