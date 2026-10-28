# Run after all module and shield libraries exist. Only the dongle uses these
# sources; existing ZEN builds and the west checkout remain unchanged.
function(zen_prepare_prospector)
  set(module_dir "${ZEPHYR_PROSPECTOR_ZMK_MODULE_MODULE_DIR}")
  set(output_dir "${PROJECT_BINARY_DIR}/zen_prospector_compat")
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../tools/prepare_prospector.py")
  execute_process(
    COMMAND "${PYTHON_EXECUTABLE}"
      "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/../tools/prepare_prospector.py"
      --source-dir "${module_dir}" --output-dir "${output_dir}"
    RESULT_VARIABLE patch_result
  )
  if(NOT patch_result EQUAL 0)
    message(FATAL_ERROR "Cannot prepare pinned Prospector compatibility fixes")
  endif()

  foreach(relative IN ITEMS
      src/split/bluetooth/central_status_changed_observer.c
      boards/shields/prospector_adapter/src/widgets/battery_bar.c)
    if(relative MATCHES "^boards/")
      set(owner_dir "${module_dir}/boards/shields/prospector_adapter")
    else()
      set(owner_dir "${module_dir}")
    endif()
    get_directory_property(owner DIRECTORY "${owner_dir}" DEFINITION ZEPHYR_CURRENT_LIBRARY)
    if(NOT TARGET "${owner}")
      message(FATAL_ERROR "Prospector source owner not found: ${relative}")
    endif()
    get_target_property(sources "${owner}" SOURCES)
    set(original "${module_dir}/${relative}")
    list(FIND sources "${original}" source_index)
    if(source_index EQUAL -1)
      message(FATAL_ERROR "Prospector source not found in ${owner}: ${relative}")
    endif()
    list(REMOVE_AT sources ${source_index})
    list(INSERT sources ${source_index} "${output_dir}/${relative}")
    set_property(TARGET "${owner}" PROPERTY SOURCES "${sources}")
    get_filename_component(original_dir "${original}" DIRECTORY)
    target_include_directories("${owner}" PRIVATE "${original_dir}")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${original}")
  endforeach()
  message(STATUS "Applied ZEN Prospector connection and widget compatibility fixes")
endfunction()

cmake_language(DEFER DIRECTORY "${APPLICATION_SOURCE_DIR}" CALL zen_prepare_prospector)
