cmake_minimum_required(VERSION 3.14)
project(CodeHound CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options(/utf-8)
endif()

# 1. Fetch Pybind11
include(FetchContent)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/pybind11-2.11.1")
    message(STATUS "Using local pybind11 from third_party")
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third_party/pybind11-2.11.1)
else()
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG        v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# 2. Fetch FlatBuffers
set(FLATBUFFERS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/flatbuffers-23.5.26")
    message(STATUS "Using local flatbuffers from third_party")
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third_party/flatbuffers-23.5.26)
else()
    FetchContent_Declare(
        flatbuffers
        GIT_REPOSITORY https://github.com/google/flatbuffers.git
        GIT_TAG        v23.5.26
    )
    FetchContent_MakeAvailable(flatbuffers)
endif()

# 3. Generate FlatBuffers C++ headers
set(SCHEMA_DIR ${CMAKE_CURRENT_SOURCE_DIR}/schema)
set(SCHEMA_FILE ${SCHEMA_DIR}/graph.fbs)

# 为 C++ 和 Python 生成文件
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/graph_generated.h
    COMMAND flatc -c -o ${CMAKE_CURRENT_BINARY_DIR} ${SCHEMA_FILE}
    COMMAND flatc -p -o ${CMAKE_CURRENT_BINARY_DIR} ${SCHEMA_FILE}
    DEPENDS ${SCHEMA_FILE} flatc
    COMMENT "Generating FlatBuffers C++ and Python headers"
)

# 4. 引擎核心库
add_library(graph_engine_core
    engine/src/graph_engine.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/graph_generated.h
)
target_include_directories(graph_engine_core PUBLIC 
    ${CMAKE_CURRENT_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/engine/src
)
target_link_libraries(graph_engine_core PUBLIC flatbuffers)

# 5. Pybind11 模块
pybind11_add_module(codegraph_engine engine/src/pybind_wrapper.cpp)
target_link_libraries(codegraph_engine PRIVATE graph_engine_core)
target_include_directories(codegraph_engine PRIVATE ${CMAKE_CURRENT_BINARY_DIR})
