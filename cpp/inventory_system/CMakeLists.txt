cmake_minimum_required(VERSION 3.16)

project(InventoryManager)

set(CMAKE_CXX_STANDARD 17)

add_executable(
    InventoryManager
    src/main.cpp
    src/InventoryManager.cpp
)

target_include_directories(
    InventoryManager
    PRIVATE include
)

target_link_libraries(
    InventorySystem
    PRIVATE nlohmann_json::nlohmann_json
)