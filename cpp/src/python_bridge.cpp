#include <Python.h>
#include "../include/stdf_parser.h"
#include "../include/dynamic_field_extractor.h"
#include "../include/ultra_fast_processor.h"
#include <iostream>
#include <vector>

// Python extension module for STDF parsing

// Helper function to safely create Python string from C++ string
static PyObject* safe_unicode_from_string(const std::string& str) {
    return PyUnicode_FromStringAndSize(str.c_str(), str.length());
}

// Convert C++ STDFRecord to Python dictionary
static PyObject* stdf_record_to_dict(const STDFRecord& record) {
    PyObject* dict = PyDict_New();
    if (!dict) return nullptr;
    
    // Basic fields
    PyDict_SetItemString(dict, "type", PyLong_FromLong(static_cast<long>(record.type)));
    PyDict_SetItemString(dict, "test_num", PyLong_FromUnsignedLong(record.test_num));
    PyDict_SetItemString(dict, "head_num", PyLong_FromUnsignedLong(record.head_num));
    PyDict_SetItemString(dict, "site_num", PyLong_FromUnsignedLong(record.site_num));
    PyDict_SetItemString(dict, "result", PyFloat_FromDouble(record.result));
    PyDict_SetItemString(dict, "alarm_id", safe_unicode_from_string(record.alarm_id));
    PyDict_SetItemString(dict, "test_txt", safe_unicode_from_string(record.test_txt));
    PyDict_SetItemString(dict, "filename", safe_unicode_from_string(record.filename));
    PyDict_SetItemString(dict, "record_index", PyLong_FromUnsignedLong(record.record_index));
    PyDict_SetItemString(dict, "wld_id", safe_unicode_from_string(record.wld_id));
    
    // Fields dictionary
    PyObject* fields_dict = PyDict_New();
    if (fields_dict) {
        for (const auto& field : record.fields) {
            PyObject* key = safe_unicode_from_string(field.first);
            PyObject* value = safe_unicode_from_string(field.second);
            if (key && value) {
                PyDict_SetItem(fields_dict, key, value);
            }
            Py_XDECREF(key);
            Py_XDECREF(value);
        }
        PyDict_SetItemString(dict, "fields", fields_dict);
    }
    
    return dict;
}

// Convert record type enum to string
static const char* record_type_to_string(STDFRecordType type) {
    switch (type) {
        case STDFRecordType::PTR: return "PTR";
        case STDFRecordType::MPR: return "MPR";
        case STDFRecordType::FTR: return "FTR";
        case STDFRecordType::HBR: return "HBR";
        case STDFRecordType::SBR: return "SBR";
        case STDFRecordType::PRR: return "PRR";
        case STDFRecordType::MIR: return "MIR";
        default: return "UNKNOWN";
    }
}

// Python function: parse_stdf_file(filepath)
static PyObject* parse_stdf_file(PyObject* self, PyObject* args) {
    const char* filepath;
    
    // Parse arguments
    if (!PyArg_ParseTuple(args, "s", &filepath)) {
        return nullptr;
    }
    
    try {
        // Create parser and parse file
        STDFParser parser;
        std::vector<STDFRecord> records = parser.parse_file(std::string(filepath));
        
        // TODO: Integrate X-Macros dynamic extraction
        // For now, the existing parser includes the basic fields
        // X-Macros integration will enhance field extraction
        
        // Convert results to Python list
        PyObject* results_list = PyList_New(records.size());
        if (!results_list) {
            return nullptr;
        }
        
        for (size_t i = 0; i < records.size(); ++i) {
            PyObject* record_dict = stdf_record_to_dict(records[i]);
            if (!record_dict) {
                Py_DECREF(results_list);
                return nullptr;
            }
            
            // Add record type string
            PyDict_SetItemString(record_dict, "record_type", 
                               PyUnicode_FromString(record_type_to_string(records[i].type)));
            
            PyList_SetItem(results_list, i, record_dict);
        }
        
        // Create return dictionary with results and statistics
        PyObject* result_dict = PyDict_New();
        PyDict_SetItemString(result_dict, "records", results_list);
        PyDict_SetItemString(result_dict, "total_records", 
                           PyLong_FromSize_t(parser.get_total_records()));
        PyDict_SetItemString(result_dict, "parsed_records", 
                           PyLong_FromSize_t(parser.get_parsed_records()));
        
        return result_dict;
        
    } catch (const std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return nullptr;
    }
}

// Python function: get_version()
static PyObject* get_version(PyObject* self, PyObject* args) {
    return PyUnicode_FromString("STDFParser C++ Extension v1.0.0");
}

// Helper function to safely extract string from Python dict
static std::string extract_dict_string(PyObject* dict, const char* key, const std::string& default_val = "") {
    if (!dict || !PyDict_Check(dict)) return default_val;
    
    PyObject* item = PyDict_GetItemString(dict, key);
    if (!item || !PyUnicode_Check(item)) return default_val;
    
    const char* str = PyUnicode_AsUTF8(item);
    return str ? std::string(str) : default_val;
}

// Option 1: Pre-compute expensive fields in C++, return to Python for object assembly
static PyObject* precompute_measurement_fields(PyObject* self, PyObject* args) {
    PyObject* mir_data_dict;
    PyObject* prr_data_dict;
    
    // Parse Python arguments
    if (!PyArg_ParseTuple(args, "OO", &mir_data_dict, &prr_data_dict)) {
        return nullptr;
    }
    
    // Pre-compute expensive operations in C++ (ONCE per test, not per measurement)
    std::string facility = extract_dict_string(mir_data_dict, "facility");
    std::string operation = extract_dict_string(mir_data_dict, "operation");
    std::string lot_name = extract_dict_string(mir_data_dict, "lot_name");
    std::string equipment = extract_dict_string(mir_data_dict, "equipment");
    std::string prog_name = extract_dict_string(mir_data_dict, "prog_name");
    std::string prog_version = extract_dict_string(mir_data_dict, "prog_version");
    std::string start_time = extract_dict_string(mir_data_dict, "start_time");
    
    std::string device_dmc = extract_dict_string(prr_data_dict, "device_dmc");
    std::string bin_code = extract_dict_string(prr_data_dict, "bin_code");
    
    // C++ logic for expensive computations (computed once, reused many times)
    bool is_pass = (bin_code == "1");
    std::string bin_desc = is_pass ? "PASS" : "FAIL";
    bool test_flag = is_pass;
    
    // Return pre-computed values as Python dict
    PyObject* computed_fields = PyDict_New();
    if (!computed_fields) return nullptr;
    
    // Set all the expensive-to-compute fields:
    PyDict_SetItemString(computed_fields, "WFI_FACILITY", PyUnicode_FromString(facility.c_str()));
    PyDict_SetItemString(computed_fields, "WFI_OPERATION", PyUnicode_FromString(operation.c_str()));
    PyDict_SetItemString(computed_fields, "WL_LOT_NAME", PyUnicode_FromString(lot_name.c_str()));
    PyDict_SetItemString(computed_fields, "WFI_EQUIPMENT", PyUnicode_FromString(equipment.c_str()));
    PyDict_SetItemString(computed_fields, "WMP_PROG_NAME", PyUnicode_FromString(prog_name.c_str()));
    PyDict_SetItemString(computed_fields, "WMP_PROG_VERSION", PyUnicode_FromString(prog_version.c_str()));
    PyDict_SetItemString(computed_fields, "WPTM_CREATED_DATE", PyUnicode_FromString(start_time.c_str()));
    PyDict_SetItemString(computed_fields, "WLD_CREATED_DATE", PyUnicode_FromString(start_time.c_str()));
    
    PyDict_SetItemString(computed_fields, "WLD_DEVICE_DMC", PyUnicode_FromString(device_dmc.c_str()));
    PyDict_SetItemString(computed_fields, "WLD_BIN_CODE", PyUnicode_FromString(bin_code.c_str()));
    PyDict_SetItemString(computed_fields, "WLD_BIN_DESC", PyUnicode_FromString(bin_desc.c_str()));
    PyDict_SetItemString(computed_fields, "TEST_FLAG", PyBool_FromLong(test_flag));
    
    // Constant fields (computed once in C++)
    PyDict_SetItemString(computed_fields, "WLD_PHOENIX_ID", PyUnicode_FromString(""));
    PyDict_SetItemString(computed_fields, "WLD_LATEST", PyUnicode_FromString("Y"));
    PyDict_SetItemString(computed_fields, "SFT_NAME", PyUnicode_FromString("STDF_CPP"));
    PyDict_SetItemString(computed_fields, "SFT_GROUP", PyUnicode_FromString("STDF_CPP"));
    
    return computed_fields;
}

// 🚀 ULTRA-FAST: Process STDF to ClickHouse tuples entirely in C++
static PyObject* process_stdf_to_clickhouse_tuples(PyObject* self, PyObject* args) {
    const char* filepath;
    
    // Parse arguments
    if (!PyArg_ParseTuple(args, "s", &filepath)) {
        return nullptr;
    }
    
    try {
        // Create ultra-fast processor
        UltraFastProcessor processor;
        
        // Process STDF file entirely in C++
        std::vector<MeasurementTuple> measurements = processor.process_stdf_file(std::string(filepath));
        
        // Convert ONLY final measurements to Python tuples (minimal bridge)
        PyObject* tuple_list = PyList_New(measurements.size());
        if (!tuple_list) {
            return nullptr;
        }
        
        // Helper function for safe string conversion
        auto PyUnicode_FromString_Safe = [](const std::string& str) -> PyObject* {
            return PyUnicode_FromString(str.c_str());
        };
        
        // 🚀 MACRO-DRIVEN: Calculate tuple size automatically
        constexpr size_t TUPLE_SIZE = 0
        #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) + 1
        #include "../include/measurement_fields.def"
        #undef MEASUREMENT_FIELD
        ;
        
        for (size_t i = 0; i < measurements.size(); ++i) {
            const auto& m = measurements[i];
            
            // Create ClickHouse-compatible tuple with auto-calculated size
            PyObject* tuple = PyTuple_New(TUPLE_SIZE);
            if (!tuple) {
                Py_DECREF(tuple_list);
                return nullptr;
            }
            
            // 🚀 MACRO-DRIVEN: Pack measurement data using macro expansion
            size_t field_index = 0;
            #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
                PyTuple_SetItem(tuple, field_index++, python_conversion(m.name));
            
            #include "../include/measurement_fields.def"
            #undef MEASUREMENT_FIELD
            
            PyList_SetItem(tuple_list, i, tuple);
        }
        
        // Create result dictionary with tuples and statistics
        PyObject* result_dict = PyDict_New();
        if (!result_dict) {
            Py_DECREF(tuple_list);
            return nullptr;
        }
        
        PyDict_SetItemString(result_dict, "measurement_tuples", tuple_list);
        PyDict_SetItemString(result_dict, "total_records", 
                           PyLong_FromSize_t(processor.get_total_records()));
        PyDict_SetItemString(result_dict, "total_measurements", 
                           PyLong_FromSize_t(processor.get_processed_measurements()));
        PyDict_SetItemString(result_dict, "parsing_time", 
                           PyFloat_FromDouble(processor.get_parsing_time()));
        PyDict_SetItemString(result_dict, "processing_time", 
                           PyFloat_FromDouble(processor.get_processing_time()));
        
        // Add ID mappings for database insertion
        const auto& id_manager = processor.get_id_manager();
        const auto& device_map = id_manager.get_device_map();
        const auto& param_map = id_manager.get_param_map();
        
        PyObject* device_mappings = PyList_New(device_map.size());
        size_t idx = 0;
        for (const auto& pair : device_map) {
            PyObject* mapping = PyTuple_New(2);
            PyTuple_SetItem(mapping, 0, PyLong_FromUnsignedLong(pair.second)); // wld_id
            PyTuple_SetItem(mapping, 1, PyUnicode_FromString(pair.first.c_str())); // device_dmc
            PyList_SetItem(device_mappings, idx++, mapping);
        }
        PyDict_SetItemString(result_dict, "device_mappings", device_mappings);
        
        PyObject* param_mappings = PyList_New(param_map.size());
        idx = 0;
        for (const auto& pair : param_map) {
            PyObject* mapping = PyTuple_New(2);
            PyTuple_SetItem(mapping, 0, PyLong_FromUnsignedLong(pair.second)); // wtp_id
            PyTuple_SetItem(mapping, 1, PyUnicode_FromString(pair.first.c_str())); // param_name
            PyList_SetItem(param_mappings, idx++, mapping);
        }
        PyDict_SetItemString(result_dict, "param_mappings", param_mappings);
        
        return result_dict;
        
    } catch (const std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return nullptr;
    }
}

// 🔧 DATABASE-AWARE: Process STDF with existing database mappings
static PyObject* process_stdf_with_database_mappings(PyObject* self, PyObject* args) {
    const char* filepath;
    PyObject* device_mappings_list;
    PyObject* param_mappings_list;
    const char* file_hash = "";
    
    // Parse arguments: filepath, device_mappings, param_mappings, file_hash (optional)
    if (!PyArg_ParseTuple(args, "sOO|s", &filepath, &device_mappings_list, &param_mappings_list, &file_hash)) {
        return nullptr;
    }
    
    try {
        // Create ultra-fast processor
        UltraFastProcessor processor;
        
        // Set the file hash from Python (MD5) to ensure consistency
        if (file_hash && strlen(file_hash) > 0) {
            processor.set_file_hash(std::string(file_hash));
            std::cout << "🔑 Using Python-generated MD5 hash: " << file_hash << std::endl;
        }
        
        // Convert Python lists to C++ vectors
        std::vector<std::pair<std::string, uint32_t>> device_mappings;
        std::vector<std::pair<std::string, uint32_t>> param_mappings;
        
        // Parse device mappings
        if (PyList_Check(device_mappings_list)) {
            Py_ssize_t size = PyList_Size(device_mappings_list);
            for (Py_ssize_t i = 0; i < size; ++i) {
                PyObject* tuple = PyList_GetItem(device_mappings_list, i);
                if (PyTuple_Check(tuple) && PyTuple_Size(tuple) == 2) {
                    PyObject* device_name = PyTuple_GetItem(tuple, 0);
                    PyObject* device_id = PyTuple_GetItem(tuple, 1);
                    
                    if (PyUnicode_Check(device_name) && PyLong_Check(device_id)) {
                        const char* name = PyUnicode_AsUTF8(device_name);
                        uint32_t id = static_cast<uint32_t>(PyLong_AsUnsignedLong(device_id));
                        device_mappings.emplace_back(name, id);
                    }
                }
            }
        }
        
        // Parse parameter mappings
        if (PyList_Check(param_mappings_list)) {
            Py_ssize_t size = PyList_Size(param_mappings_list);
            for (Py_ssize_t i = 0; i < size; ++i) {
                PyObject* tuple = PyList_GetItem(param_mappings_list, i);
                if (PyTuple_Check(tuple) && PyTuple_Size(tuple) == 2) {
                    PyObject* param_name = PyTuple_GetItem(tuple, 0);
                    PyObject* param_id = PyTuple_GetItem(tuple, 1);
                    
                    if (PyUnicode_Check(param_name) && PyLong_Check(param_id)) {
                        const char* name = PyUnicode_AsUTF8(param_name);
                        uint32_t id = static_cast<uint32_t>(PyLong_AsUnsignedLong(param_id));
                        param_mappings.emplace_back(name, id);
                    }
                }
            }
        }
        
        std::cout << "🔧 Loading " << device_mappings.size() << " device mappings, " 
                  << param_mappings.size() << " parameter mappings from database" << std::endl;
        
        // Load existing mappings into processor
        auto& id_manager = const_cast<FastIDManager&>(processor.get_id_manager());
        id_manager.load_existing_mappings_from_python(device_mappings, param_mappings);
        
        // Process STDF file with database-aware IDs
        std::vector<MeasurementTuple> measurements = processor.process_stdf_file(std::string(filepath));
        
        // Convert measurements to Python tuples (reuse existing code)
        auto PyUnicode_FromString_Safe = [](const std::string& str) -> PyObject* {
            return PyUnicode_FromString(str.c_str());
        };
        
        constexpr size_t TUPLE_SIZE = 0
        #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) + 1
        #include "../include/measurement_fields.def"
        #undef MEASUREMENT_FIELD
        ;
        
        PyObject* tuple_list = PyList_New(measurements.size());
        if (!tuple_list) return nullptr;
        
        for (size_t i = 0; i < measurements.size(); ++i) {
            const auto& m = measurements[i];
            
            PyObject* tuple = PyTuple_New(TUPLE_SIZE);
            if (!tuple) {
                Py_DECREF(tuple_list);
                return nullptr;
            }
            
            size_t field_index = 0;
            #define MEASUREMENT_FIELD(name, cpp_type, python_conversion, clickhouse_type) \
                PyTuple_SetItem(tuple, field_index++, python_conversion(m.name));
            
            #include "../include/measurement_fields.def"
            #undef MEASUREMENT_FIELD
            
            PyList_SetItem(tuple_list, i, tuple);
        }
        
        // Get only new mappings for database insertion
        auto new_device_mappings = id_manager.get_new_device_mappings();
        auto new_param_mappings = id_manager.get_new_param_mappings();
        
        std::cout << "🆕 Found " << new_device_mappings.size() << " new devices, " 
                  << new_param_mappings.size() << " new parameters to insert" << std::endl;
        
        // Create result dictionary
        PyObject* result_dict = PyDict_New();
        if (!result_dict) {
            Py_DECREF(tuple_list);
            return nullptr;
        }
        
        PyDict_SetItemString(result_dict, "measurement_tuples", tuple_list);
        PyDict_SetItemString(result_dict, "total_records", 
                           PyLong_FromSize_t(processor.get_total_records()));
        PyDict_SetItemString(result_dict, "total_measurements", 
                           PyLong_FromSize_t(processor.get_processed_measurements()));
        PyDict_SetItemString(result_dict, "parsing_time", 
                           PyFloat_FromDouble(processor.get_parsing_time()));
        PyDict_SetItemString(result_dict, "processing_time", 
                           PyFloat_FromDouble(processor.get_processing_time()));
        
        // Add only NEW mappings for database insertion
        PyObject* new_device_list = PyList_New(new_device_mappings.size());
        for (size_t i = 0; i < new_device_mappings.size(); ++i) {
            PyObject* mapping = PyTuple_New(2);
            PyTuple_SetItem(mapping, 0, PyUnicode_FromString(new_device_mappings[i].first.c_str()));
            PyTuple_SetItem(mapping, 1, PyLong_FromUnsignedLong(new_device_mappings[i].second));
            PyList_SetItem(new_device_list, i, mapping);
        }
        PyDict_SetItemString(result_dict, "new_device_mappings", new_device_list);
        
        PyObject* new_param_list = PyList_New(new_param_mappings.size());
        for (size_t i = 0; i < new_param_mappings.size(); ++i) {
            PyObject* mapping = PyTuple_New(2);
            PyTuple_SetItem(mapping, 0, PyUnicode_FromString(new_param_mappings[i].first.c_str()));
            PyTuple_SetItem(mapping, 1, PyLong_FromUnsignedLong(new_param_mappings[i].second));
            PyList_SetItem(new_param_list, i, mapping);
        }
        PyDict_SetItemString(result_dict, "new_param_mappings", new_param_list);
        
        return result_dict;
        
    } catch (const std::exception& e) {
        PyErr_SetString(PyExc_RuntimeError, e.what());
        return nullptr;
    }
}

// Method definitions
static PyMethodDef StdfParserMethods[] = {
    {"parse_stdf_file", parse_stdf_file, METH_VARARGS,
     "Parse STDF file and return list of records"},
    {"precompute_measurement_fields", precompute_measurement_fields, METH_VARARGS,
     "Pre-compute expensive measurement fields in C++"},
    {"process_stdf_to_clickhouse_tuples", process_stdf_to_clickhouse_tuples, METH_VARARGS,
     "🚀 ULTRA-FAST: Process STDF to ClickHouse tuples entirely in C++"},
    {"process_stdf_with_database_mappings", process_stdf_with_database_mappings, METH_VARARGS,
     "🔧 DATABASE-AWARE: Process STDF with existing database mappings and optional file hash"},
    {"get_version", get_version, METH_NOARGS,
     "Get version information"},
    {nullptr, nullptr, 0, nullptr}
};

// Module definition
static struct PyModuleDef stdf_parser_module = {
    PyModuleDef_HEAD_INIT,
    "stdf_parser_cpp",
    "High-performance STDF parser using C++",
    -1,
    StdfParserMethods
};

// Module initialization
PyMODINIT_FUNC PyInit_stdf_parser_cpp(void) {
    PyObject* module = PyModule_Create(&stdf_parser_module);
    if (!module) {
        return nullptr;
    }
    
    // Add constants for record types
    PyModule_AddIntConstant(module, "PTR", static_cast<int>(STDFRecordType::PTR));
    PyModule_AddIntConstant(module, "MPR", static_cast<int>(STDFRecordType::MPR));
    PyModule_AddIntConstant(module, "FTR", static_cast<int>(STDFRecordType::FTR));
    PyModule_AddIntConstant(module, "HBR", static_cast<int>(STDFRecordType::HBR));
    PyModule_AddIntConstant(module, "SBR", static_cast<int>(STDFRecordType::SBR));
    PyModule_AddIntConstant(module, "PRR", static_cast<int>(STDFRecordType::PRR));
    PyModule_AddIntConstant(module, "MIR", static_cast<int>(STDFRecordType::MIR));
    
    return module;
}