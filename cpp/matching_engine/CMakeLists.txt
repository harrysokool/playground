cmake_minimum_required(VERSION 3.16)

project(MatchingEngine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.17.0.zip
)

set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(googletest)

# Core matching-engine library
add_library(
    order_book_lib
    src/OrderBook.cpp
)

target_include_directories(
    order_book_lib
    PUBLIC
    include
)

target_compile_options(
    order_book_lib
    PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)

# Main executable
add_executable(
    matching_engine
    src/main.cpp
)

target_link_libraries(
    matching_engine
    PRIVATE
    order_book_lib
)

# Tests
enable_testing()

add_executable(
    order_book_tests
    tests/OrderBookTests.cpp
)

target_link_libraries(
    order_book_tests
    PRIVATE
    order_book_lib
    GTest::gtest_main
)

include(GoogleTest)

gtest_discover_tests(order_book_tests)

# Benchmark
add_executable(
    matching_benchmark
    benchmarks/MatchingBenchmark.cpp
)

target_link_libraries(
    matching_benchmark
    PRIVATE
    order_book_lib
)

# Optional sanitizers
option(
    ENABLE_SANITIZERS
    "Enable AddressSanitizer and UndefinedBehaviorSanitizer"
    OFF
)

if(ENABLE_SANITIZERS)
    target_compile_options(
        order_book_lib
        PRIVATE
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
    )

    target_link_options(
        order_book_lib
        PRIVATE
        -fsanitize=address,undefined
    )

    target_compile_options(
        order_book_tests
        PRIVATE
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
    )

    target_link_options(
        order_book_tests
        PRIVATE
        -fsanitize=address,undefined
    )
endif()