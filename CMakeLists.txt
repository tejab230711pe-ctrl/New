cmake_minimum_required(VERSION 3.16)

# Project name
project(RotatingDiskDepositionApp LANGUAGES CXX)

# Find MOOSE (expects MOOSE_DIR environment variable or a cmake config file)
set(MOOSE_MODULES TensorMechanics)
find_package(MOOSE REQUIRED)

# Add source files
set(SRC_FILES
    src/AA5083ThermalProperties.C
    src/FrictionHeatSource.C
    src/NormalServo.C
    src/MushyFraction.C
    src/RotatingDiskDepositionApp.C
)

# Build the application
add_executable(${PROJECT_NAME} ${SRC_FILES})

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)

target_link_libraries(${PROJECT_NAME} PRIVATE MOOSE::Moose)

# Install the executable
install(TARGETS ${PROJECT_NAME} RUNTIME DESTINATION bin)

# If you have any tests, enable them here (optional)
# enable_testing()
# add_subdirectory(test)
