#ifndef MEASUREMENT_MACROS_H
#define MEASUREMENT_MACROS_H

// 🚀 MACRO-DRIVEN: Helper macros for measurement field assignment

// Macro to create a measurement initializer function
#define INIT_MEASUREMENT(measurement, device_dmc, device_id, test_cache, value, test_flag, file_hash_param) \
    do { \
        measurement.wld_id = device_id; \
        measurement.wtp_id = test_cache.param_id; \
        measurement.wp_pos_x = (test_cache.pixel_x != 0) ? test_cache.pixel_x : default_x; \
        measurement.wp_pos_y = (test_cache.pixel_y != 0) ? test_cache.pixel_y : default_y; \
        measurement.wptm_value = value; \
        measurement.test_flag = test_flag; \
        measurement.segment = 0; \
        measurement.file_hash = file_hash_param; \
        measurement.wld_device_dmc = device_dmc; \
        measurement.wtp_param_name = test_cache.cleaned_param_name; \
        measurement.units = test_cache.units; \
        measurement.test_num = test_cache.test_num; \
        measurement.test_flg = test_cache.test_flg; \
    } while(0)

// Macro to generate ClickHouse table schema from field definitions  
#define GENERATE_CLICKHOUSE_SCHEMA() \
    std::string schema = "CREATE TABLE IF NOT EXISTS measurements (\n"; \
    bool first = true; \
    auto add_field = [&](const std::string& name, const std::string& type) { \
        if (!first) schema += ",\n"; \
        schema += "    " + name + " " + type; \
        first = false; \
    }; \
    \
    /* Add all fields from measurement_fields.def */ \
    add_field("wptm_created_date", "DateTime"); \
    \
    /* Add fields using macro expansion */ \
    _Pragma("GCC diagnostic push") \
    _Pragma("GCC diagnostic ignored \"-Wunused-variable\"") \
    { \
        auto add_measurement_field = [&](const std::string& n, const std::string& t) { add_field(n, t); }; \
        std::string name, type; /* Dummy variables */ \
        \
        schema += "\n) ENGINE = MergeTree()\n"; \
        schema += "PARTITION BY toYYYYMM(wptm_created_date)\n"; \
        schema += "ORDER BY (wld_id, wtp_id, wp_pos_x, wp_pos_y, segment)"; \
    } \
    _Pragma("GCC diagnostic pop")

// Macro to count fields automatically
#define COUNT_MEASUREMENT_FIELDS() (0 \
    FIELD_COUNTER \
)

#define FIELD_COUNTER \
    + 1 /* wld_id */ \
    + 1 /* wtp_id */ \
    + 1 /* wp_pos_x */ \
    + 1 /* wp_pos_y */ \
    + 1 /* wptm_value */ \
    + 1 /* test_flag */ \
    + 1 /* segment */ \
    + 1 /* file_hash */ \
    + 1 /* wld_device_dmc */ \
    + 1 /* wtp_param_name */ \
    + 1 /* units */ \
    + 1 /* test_num */ \
    + 1 /* test_flg */

#endif // MEASUREMENT_MACROS_H