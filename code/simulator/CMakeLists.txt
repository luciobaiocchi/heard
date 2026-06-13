cmake_minimum_required(VERSION 3.14)
project(heard_sim CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── pybind11 ─────────────────────────────────────────────────────────────
# Pass -DPYTHON_EXECUTABLE=$(which python3) to match the Python that runs tests.
if(NOT DEFINED PYTHON_EXECUTABLE)
    find_program(PYTHON_EXECUTABLE python3)
endif()

# Query pybind11 cmake dir from the chosen Python — set pybind11_DIR explicitly
# so cmake cannot pick up a pybind11 belonging to a different Python install.
execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _pb11_result
)
if(NOT _pb11_result EQUAL 0)
    message(FATAL_ERROR
        "pybind11 not found for ${PYTHON_EXECUTABLE}.\n"
        "Install it with:  ${PYTHON_EXECUTABLE} -m pip install pybind11")
endif()

set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 REQUIRED PATHS "${pybind11_DIR}" NO_DEFAULT_PATH)

# ── Include paths ─────────────────────────────────────────────────────────
set(FIRMWARE_ROOT "${CMAKE_SOURCE_DIR}/../core")

include_directories(
    "${FIRMWARE_ROOT}/include"
    "${CMAKE_SOURCE_DIR}/mocks"   # provides Arduino.h, freertos/, SPI.h, LoRa.h
    "${CMAKE_SOURCE_DIR}"         # provides sim/SimConnection.h, sim/SimDevice.h
)

# ── Sources ───────────────────────────────────────────────────────────────
set(SRCS
    # Firmware — Connection.cpp provides RTTI symbols for the base class;
    # its LoRa/Serial calls resolve to no-op stubs from mocks/.
    "${FIRMWARE_ROOT}/src/group/Connection.cpp"
    "${FIRMWARE_ROOT}/src/group/ConnectionManager.cpp"

    # Simulator shims
    "${CMAKE_SOURCE_DIR}/sim/SimConnection.cpp"
    "${CMAKE_SOURCE_DIR}/sim/SimDevice.cpp"

    # pybind11 module entry point
    "${CMAKE_SOURCE_DIR}/bindings.cpp"
)

pybind11_add_module(heard_sim ${SRCS})

# Suppress warnings from firmware code that we cannot change
target_compile_options(heard_sim PRIVATE
    -Wno-unused-parameter
    -Wno-unused-variable
)
