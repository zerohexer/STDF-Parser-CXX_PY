#include <Python.h>
#include "../include/stdf_parser.h"
#include "../include/dynamic_field_extractor.h"
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

// Method definitions
static PyMethodDef StdfParserMethods[] = {
    {"parse_stdf_file", parse_stdf_file, METH_VARARGS,
     "Parse STDF file and return list of records"},
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