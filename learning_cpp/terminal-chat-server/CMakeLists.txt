cmake_minimum_required(VERSION 3.16)

project(terminal-chat-server)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(
    terminal-chat-server
    src/main.cpp
)