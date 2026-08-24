cmake_minimum_required(VERSION 3.16)

project(MatchingEngine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(matching_engine
src/main.cpp
src/OrderBook.cpp
)

target_include_directories(matching_engine PRIVATE include)

target_compile_options(matching_engine PRIVATE
-Wall
-Wextra
-Wpedantic
)

add_executable(order_book_tests
    tests/OrderBookTests.cpp
    src/OrderBook.cpp
)

target_include_directories(order_book_tests PRIVATE include)

target_compile_options(order_book_tests PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)