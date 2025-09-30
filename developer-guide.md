---
marp: true
theme: default
paginate: true
backgroundColor: #ffffff
color: #000000
style: |
  :root {
    --osram-orange: #FF6600;
    --osram-light-orange: #FF8533;
    --grey-heading: #666666;
    --light-grey: #f5f5f5;
    --flow-bg: #f8f9fa;
    --box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    --base-font-size: 0.7em;
  }

  section {
    background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: var(--base-font-size);
    padding: 40px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: stretch;
    text-align: left;
  }

  h1, h2, h3, h4, h5, h6 {
    color: var(--grey-heading);
    border-bottom: 3px solid var(--osram-orange);
    padding-bottom: 10px;
    margin-top: 0;
    margin-bottom: 20px;
    text-align: left;
  }

  h1 {
    font-weight: bold;
  }

  table {
    border-collapse: collapse;
    margin: 20px 0;
    width: 100%;
  }

  th {
    background: var(--osram-orange);
    color: white;
    padding: 12px;
    text-align: left;
  }

  td {
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
  }

  tr:nth-child(even) {
    background: var(--light-grey);
  }

  .data-flow {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 20px 0;
    flex-wrap: wrap;
    gap: 10px;
  }

  .flow-item {
    background: var(--flow-bg);
    border: 2px solid var(--osram-orange);
    border-radius: 8px;
    padding: 12px 20px;
    font-weight: bold;
    color: var(--grey-heading);
    min-width: 120px;
    text-align: center;
  }

  .flow-arrow {
    color: var(--osram-orange);
    font-size: 1.5em;
    font-weight: bold;
    margin: 0 10px;
  }

  .process-box {
    background: var(--light-grey);
    padding: 10px;
    margin: 6px 0;
    border-radius: 4px;
  }

  .highlight {
    background: var(--osram-light-orange);
    color: white;
    padding: 2px 6px;
    border-radius: 3px;
  }

  .architecture-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 20px 0;
  }

  .arch-component {
    background: var(--flow-bg);
    border: 1px solid var(--osram-orange);
    border-radius: 8px;
    padding: 15px;
    text-align: center;
  }

  .step-number {
    background: var(--osram-orange);
    color: white;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    margin-right: 10px;
  }

  blockquote {
    border-left: 5px solid var(--osram-orange);
    background: var(--light-grey);
    padding: 15px;
    margin: 20px 0;
  }

  footer {
    color: var(--grey-heading);
    border-top: 2px solid var(--osram-orange);
  }
---

# **STDF Parser Developer Guide**
## High-Performance Semiconductor Test Data Processing

From Binary Files to Structured Measurement

---

# **System Architecture Overview**

<div class="data-flow">
  <div class="flow-item">STDF Binary File</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">libstdf Parser</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">C++ Processing</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Measurement Tuples</div>
</div>

**Two-Layer Architecture:**

<div class="architecture-grid">
  <div class="arch-component">
    <strong>Layer 1: libstdf</strong><br>
    Low-level file parsing<br>
    Compression handling<br>
    Record extraction
  </div>
  <div class="arch-component">
    <strong>Layer 2: C++ Parser</strong><br>
    X-Macro field extraction<br>
    Measurement processing<br>
    ID mapping & optimization
  </div>
</div>

**Performance Target:** 30+ MB files in 3-4s parsing | 177 MB (6 files) in 20s total (Python parallel)

---

# **libstdf Foundation**

**What libstdf Provides:**

<div class="process-box">
<strong>Core Functionality:</strong><br>
• Opens STDF files with automatic compression detection (ZIP, GZIP, BZIP2)<br>
• Handles byte order conversion (little-endian ↔ big-endian)<br>
• Reads records as structured C types (rec_ptr, rec_mir, rec_prr, etc.)<br>
• Manages memory allocation and cleanup
</div>

**Basic libstdf Usage:**

```c
// Open STDF file
stdf_file* file = stdf_open("test_data.stdf");

// Read records one by one
rec_unknown* record;
while ((record = stdf_read_record(file)) != nullptr) {
    // Check record type
    if (HEAD_TO_REC(record->header) == REC_PTR) {
        rec_ptr* ptr = (rec_ptr*)record;  // Safe cast
        // Access fields: ptr->TEST_NUM, ptr->RESULT, etc.
    }
    stdf_free_record(record);  // Always cleanup
}

stdf_close(file);
```

**Key Insight:** libstdf provides type-safe C structures for all STDF record types, eliminating manual binary parsing

---

# **STDF Record Types & Structures**

**Main Record Types in Our Parser:**

| Record Type | libstdf Structure | Purpose |
|-------------|-------------------|---------|
| PTR | `rec_ptr` | Parametric Test Record - single measurement |
| MPR | `rec_mpr` | Multiple-Result Parametric - array of values |
| FTR | `rec_ftr` | Functional Test Record |
| PRR | `rec_prr` | Part Result Record - device info, pass/fail |
| MIR | `rec_mir` | Master Information Record - lot/equipment data |

**Example libstdf Structure:**

```c
typedef struct {
    rec_header header;   // Common 4-byte header
    dtc_U4 TEST_NUM;    // Test number (uint32_t)
    dtc_U1 HEAD_NUM;    // Head number (uint8_t)
    dtc_R4* RESULT;     // Test result (float pointer)
    dtc_Cn TEST_TXT;    // Test name (length-prefixed string)
    dtc_Cn ALARM_ID;    // Parameter name (length-prefixed string)
    // ... more fields
} rec_ptr;
```

**String Handling:** libstdf uses length-prefixed strings (first byte = length)
```c
dtc_Cn name = ptr->TEST_TXT;
uint8_t length = name[0];           // Get length
std::string str(name + 1, length);  // Extract data
```

---

# **C++ Parser Architecture**

<div class="data-flow">
  <div class="flow-item">libstdf Records</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">STDFParser</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">X-Macro Extraction</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">UltraFastProcessor</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Measurements</div>
</div>

**Key Components in `/cpp/src/`:**

<div class="architecture-grid">
  <div class="arch-component">
    <strong>stdf_parser.cpp</strong><br>
    Main parsing orchestration<br>
    Record type routing<br>
    File handling
  </div>
  <div class="arch-component">
    <strong>dynamic_field_extractor.cpp</strong><br>
    X-Macro field extraction<br>
    Template specializations<br>
    Type conversions
  </div>
  <div class="arch-component">
    <strong>ultra_fast_processor.cpp</strong><br>
    Measurement creation<br>
    ID mapping<br>
    Cross-product processing
  </div>
</div>

**Processing Flow:**
1. STDFParser opens file via libstdf
2. Routes records to specialized parsers
3. DynamicFieldExtractor uses X-Macros for field extraction
4. UltraFastProcessor creates measurement tuples

---

# **What Does STDFParser Do?**

**Core Functionality: Parse Binary STDF → Structured Records**


<div class="data-flow">
  <div class="flow-item">Binary STDF File</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Read Record</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Identify Type</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Extract Fields</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">STDFRecord</div>
</div>

**Step-by-Step Parsing Process:**
<div class="process-box">
<span class="step-number">1</span><strong>Open File</strong><br>
<code>stdf_file* file = stdf_open("test.stdf");</code><br>
Uses libstdf to handle compression, byte order
</div>

<div class="process-box">
<span class="step-number">2</span><strong>Read Record Loop</strong><br>
<code>while ((rec = stdf_read_record(file)) != nullptr)</code><br>
Reads one record at a time from file
</div>

<div class="process-box">
<span class="step-number">3</span><strong>Identify Record Type</strong><br>
<code>if (HEAD_TO_REC(rec->header) == REC_PTR)</code><br>
Checks 4-byte header to determine PTR, MPR, FTR, etc.
</div>

---
<div class="process-box">
<span class="step-number">4</span><strong>Cast to Correct Type</strong><br>
<code>rec_ptr* ptr = (rec_ptr*)rec;</code><br>
Safely casts to libstdf structure for field access
</div>

<div class="process-box">
<span class="step-number">5</span><strong>Extract Fields</strong><br>
<code>record.fields = extract_all_fields(ptr);</code><br>
Reads all fields from libstdf structure → string map
</div>

<div class="process-box">
<span class="step-number">6</span><strong>Store Record</strong><br>
<code>records.push_back(record);</code><br>
Adds to vector of parsed records
</div>

**Key Insight:** STDFParser is the orchestrator - it uses libstdf for low-level reading, routes records by type, and delegates field extraction. It doesn't hardcode field logic!

**Complete Parsing Code (Steps 3-6):**

```cpp
// Step 3: Identify record type from header
if (HEAD_TO_REC(rec->header) == REC_PTR) {
    // Step 4: Cast to correct libstdf type
    rec_ptr* ptr = (rec_ptr*)rec;

    // Step 5: Extract fields (via X-Macros or manual)
    STDFRecord record;
    record.type = STDFRecordType::PTR;
    record.fields = extract_all_fields(ptr);  // X-Macros populate this
    // Without X-Macros: record.fields["TEST_NUM"] = std::to_string(ptr->TEST_NUM); // Manual!

    // Step 6: Store in results vector
    records.push_back(record);
}
else if (HEAD_TO_REC(rec->header) == REC_MPR) {
    rec_mpr* mpr = (rec_mpr*)rec;
    STDFRecord record;
    record.type = STDFRecordType::MPR;
    record.fields = extract_all_fields(mpr);
    records.push_back(record);
}
// ... similar for FTR, HBR, SBR, PRR, MIR
```

---

# **X-Macro System**

**Problem:** Writing field extraction code for 50+ fields × 7 record types = 350+ repetitive lines

**Solution:** X-Macros - Compile-time code generation

**Step 1: Define Fields Once (.def file):**

```cpp
// cpp/field_defs/ptr_fields.def
FIELD("TEST_NUM", TEST_NUM)
FIELD("HEAD_NUM", HEAD_NUM)
FIELD("SITE_NUM", SITE_NUM)
FIELD("TEST_FLG", TEST_FLG)
FIELD("RESULT", RESULT)
FIELD("TEST_TXT", TEST_TXT)
FIELD("ALARM_ID", ALARM_ID)
FIELD("UNITS", UNITS)
```

**Step 2: Template Generates All Code:**

```cpp
// cpp/src/dynamic_field_extractor.cpp
template<>
void DynamicFieldExtractor::extract_fields<rec_ptr>(rec_ptr* ptr, DynamicSTDFRecord& out) {
    #define FIELD(name, member) \
        if (enabled.count(name)) { \
            out.fields[name] = field_to_string(ptr->member); \
        }

    #include "../field_defs/ptr_fields.def"  // Auto-expands ALL fields
    #undef FIELD
}
```

**Result:** Add new field = 1 line in .def file. No manual coding needed!

---

# **Why X-Macros? The Real Benefits**

**Comparison: Manual vs X-Macro Field Extraction**

| Aspect | Manual Approach (Old) | X-Macro Approach (New) |
|--------|----------------------|------------------------|
| **Total Lines of Code** | ~210 lines across 7 parse functions | ~50 lines (template + .def files) |
| **Code Duplication** | Copy-paste pattern for each record type | ONE template handles all types |
| **Adding New Field** | Add 1 line in C++ function | Add 1 line in .def file |
| **Field Naming** | Manually enforced (lowercase) | Automatically enforced (UPPERCASE) |
| **Type Conversions** | Inline null checks everywhere | Centralized `field_to_string()` helper |

**Real Code Examples:**

<div class="process-box">
<strong>Manual (Old - 210 lines total):</strong><br>
<code>// parse_ptr_record() - 14 lines for 6 fields<br>
record.fields["test_num"] = std::to_string(ptr->TEST_NUM);<br>
record.fields["result"] = std::to_string(ptr->RESULT);<br>
// ... repeat for MPR (40 lines), FTR (50 lines), etc.</code>
</div>

<div class="process-box">
<strong>X-Macro (New - 50 lines total):</strong><br>
<code>// ONE template for ALL types (8 lines)<br>
g_field_extractor.extract_fields(ptr, record);<br>
// Fields defined in data files (ptr_fields.def, mpr_fields.def, etc.)</code>
</div>

**Reusable** - Same template works for PTR, MPR, FTR, HBR, SBR, PRR, MIR


**Key Insight:** X-Macros don't make adding fields "easier" (both require 1 line), but they eliminate 160+ lines of repetitive code and enforce consistency across all record types!

---

# **Modifying Field Extraction**

**To Add a New Field to PTR Records:**

<div class="process-box">
<strong>Single Line Change:</strong><br>
Edit <code>cpp/field_defs/ptr_fields.def</code> and add one line
</div>

**Example - Adding LO_LIMIT field:**

```cpp
// cpp/field_defs/ptr_fields.def
FIELD("TEST_NUM", TEST_NUM)
FIELD("RESULT", RESULT)
FIELD("LO_LIMIT", LO_LIMIT)     // ← Add this line
FIELD("HI_LIMIT", HI_LIMIT)     // ← Add this line
FIELD("UNITS", UNITS)
```

**That's it! Recompile and the field is automatically extracted.**

**To Add a New Record Type:**

1. Create new `.def` file: `cpp/field_defs/new_record_fields.def`
2. Add template specialization in `dynamic_field_extractor.cpp`:

```cpp
template<>
void DynamicFieldExtractor::extract_fields<rec_new>(rec_new* rec, DynamicSTDFRecord& out) {
    #define FIELD(name, member) if (enabled.count(name)) { out.fields[name] = field_to_string(rec->member); }
    #include "../field_defs/new_record_fields.def"
    #undef FIELD
}
```

**X-Macros = Data-Driven Programming**

---

# **Two Processing Modes**

**The parser supports two distinct use cases:**

<div class="architecture-grid">
  <div class="arch-component">
    <strong>1. Field Extraction</strong><br>
    Extract ALL fields from records<br>
    Get structured record data<br>
    Complete record information
  </div>
  <div class="arch-component">
    <strong>2. Measurement Extraction</strong><br>
    Optimized measurement pipeline<br>
    Fast cross-product processing<br>
    Database-ready tuples
  </div>
</div>

**When to Use Each:**

| Mode | Purpose | Output |
|------|---------|-----------|
| **Field Extraction** | Debug, analysis, record inspection | `STDFRecord` with all fields |
| **Measurement Extraction** | Production data processing | `MeasurementTuple` optimized |

<div class="process-box">
<strong>Key Difference:</strong><br>
Field extraction gives you access to ALL record fields via X-Macros. Measurement extraction is optimized for creating measurement tuples with only the fields needed for analysis.
</div>

**Both modes available in Python and C++, both use C++ under the hood.**

---

# **Two Ways to Extract Fields (C++ Layer)**

**Both Python and C++ go through the C++ layer - the question is HOW the C++ layer extracts fields:**

<div class="architecture-grid">
  <div class="arch-component">
    <strong>1. X-Macro Extraction (Recommended)</strong><br>
    C++ reads .def files at compile-time<br>
    Automatic field population<br>
    No manual code needed
  </div>
  <div class="arch-component">
    <strong>2. Manual Extraction (Legacy)</strong><br>
    C++ developer hardcodes field assignments<br>
    Direct libstdf member access in C++ code<br>
    Requires C++ code changes
  </div>
</div>

<div class="process-box">
<strong>Key Point:</strong> Python ALWAYS calls C++ under the hood. Both extraction methods happen in the C++ layer - Python just receives the populated <code>fields</code> dictionary regardless of whether C++ used X-Macros or manual code.
</div>


| Approach | How It Works (C++ Layer) | Adding New Field | Consistency | Python Access |
|----------|--------------------------|------------------|-------------|---------------|
| **X-Macro (.def files)** | `FIELD("TEST_NUM", TEST_NUM)` in .def → C++ automatic | Edit 1 line in .def file |  UPPERCASE, no duplicates | `fields['TEST_NUM']` |
| **Manual (Direct code)** | `record.fields["test_num"] = std::to_string(ptr->TEST_NUM);` in C++ | Write C++ code, rebuild |  lowercase/UPPERCASE conflicts | `fields['test_num']` |

---
**X-Macro Extraction Example (.def file):**

```cpp
// cpp/field_defs/ptr_fields.def
FIELD("TEST_NUM", TEST_NUM)
FIELD("RESULT", RESULT)
FIELD("TEST_TXT", TEST_TXT)
FIELD("ALARM_ID", ALARM_ID)
// Add new field: just 1 line!
```

**Manual Extraction Example (C++ code):**

```cpp
// cpp/src/stdf_parser.cpp (legacy approach)
record.fields["test_num"] = std::to_string(ptr->TEST_NUM);
record.fields["result"] = ptr->RESULT ? std::to_string(*ptr->RESULT) : "";
record.fields["test_txt"] = extract_string(ptr->TEST_TXT);
// Must write C++ for each field manually
```

**Current Status:** Migrated to X-Macro (.def) approach for all standard STDF fields. Manual extraction only for internal fields.

---

# **Field Extraction Usage**

**Python Field Extraction (via X-Macros):**

```python
import stdf_parser_cpp

# Parse STDF file - X-Macros populate ALL fields automatically
result = stdf_parser_cpp.parse_stdf_file("test.stdf")

# Fields populated from .def files via X-Macros under the hood
for record in result['records']:
    record_type = record['record_type']  # 'PTR', 'MPR', 'FTR', etc.
    fields = record['fields']  # X-Macro extracted fields

    if record_type == 'PTR':
        print(f"TEST_NUM: {fields['TEST_NUM']}")
        print(f"RESULT: {fields['RESULT']}")
        ....
        # ... all 20 PTR fields from ptr_fields.def

    elif record_type == 'PRR':
        print(f"PART_ID: {fields['PART_ID']}")
        ...
        # ... all 9 PRR fields from prr_fields.def
```

**C++ Field Extraction (via X-Macros):**

```cpp
#include "cpp/include/stdf_parser.h"

STDFParser parser;
auto records = parser.parse_file("test.stdf");

// X-Macros populate record.fields map from .def files
for (const auto& record : records) {
    if (record.type == STDFRecordType::PTR) {
        // Fields auto-populated from cpp/field_defs/ptr_fields.def
        std::cout << "TEST_NUM: " << record.fields.at("TEST_NUM") << "\n";
        std::cout << "RESULT: " << record.fields.at("RESULT") << "\n";
        ....
    }
    else if (record.type == STDFRecordType::HBR) {
        // Fields auto-populated from cpp/field_defs/hbr_fields.def
        std::cout << "HBIN_NUM: " << record.fields.at("hbin_num") << "\n";
        ....
    }
}
```


---

# **Measurement Extraction Pipeline**

**From STDF Records to Measurement Tuples:**

<div class="data-flow">
  <div class="flow-item">Parse Records</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Extract Fields</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Cross Product</div>
  <div class="flow-arrow">→</div>
  <div class="flow-item">Measurement Tuples</div>
</div>

**The Cross-Product Logic:**

```cpp
// UltraFastProcessor::process_cross_product_measurements()
for (const auto& prr : prr_records) {        // Each device
    std::string device_dmc = get_field(prr, "PART_ID");
    uint32_t device_id = id_manager_.get_device_id(device_dmc);

    for (const auto& test : test_records) {  // Each test
        std::string param_name = get_field(test, "ALARM_ID");
        uint32_t param_id = id_manager_.get_param_id(param_name);

        for (double value : parse_values(test)) {  // Each value
            MeasurementTuple measurement;
            measurement.wld_id = device_id;
            measurement.wtp_id = param_id;
            measurement.wptm_value = value;
            // ... more fields via X-Macros
            measurements.push_back(measurement);
        }
    }
}
```

**Performance:** Pre-allocates memory, uses hash maps (O(1) lookups), processes millions of measurements in seconds

---

# **Performance Results**

**Benchmark: 30-35 MB STDF Files**

<div class="process-box">
<strong>Timing Breakdown:</strong><br>
• libstdf parsing: ~1.5 seconds<br>
• Field extraction: ~0.5 seconds<br>
• Measurement creation: ~1.0 seconds<br>
<strong>Total: 3-4 seconds</strong>
</div>

**Performance Characteristics:**

| File Size | Records | Measurements | Time | Throughput |
|-----------|---------|--------------|------|------------|
| 30 MB | ~500K | ~1.5M | 3.2s | 470K meas/sec |
| 35 MB | ~600K | ~1.8M | 3.8s | 470K meas/sec |

**Optimization Techniques:**
- **Memory:** Stream processing, immediate cleanup, pre-allocation
- **CPU:** Hash maps for O(1) lookups, pre-compiled regex, X-Macro compile-time generation
- **I/O:** libstdf's buffered reading, single-pass processing

**Real-World Impact:** Process 100 files (3 GB) in ~5 minutes with parallel processing

---

# **Real-World Performance Benchmark**

**Single File: 35 MB STDF (3.7M Measurements)**

| Implementation | Total Time | C++ Processing | Python Overhead | Throughput |
|----------------|------------|----------------|-----------------|------------|
| Python | 12.16s | 9.06s | 3.1s | 407K meas/s |
| C++ Direct | 8.78s | 8.04s | 0.74s | 459K meas/s |

**Multiple Files: 6 STDF Files (177 MB Total, 17.3M Measurements)**

<div class="process-box">
<strong>Python Parallel (ProcessPoolExecutor, 3 workers):</strong><br>
• Total time: <strong>20.29 seconds</strong><br>
• Throughput: 852K measurements/second<br>
</div>

<div class="process-box">
<strong>C++ Parallel (std::async, 3 threads):</strong><br>
• Total time: <strong>33.13 seconds</strong><br>
• Throughput: 521K measurements/second<br>
</div>

**Individual File Performance (Parallel Mode):**

| File Size | Records | Measurements | Parsing Time | Total Time | Throughput |
|-----------|---------|--------------|--------------|------------|------------|
| ~30 MB | 71K | 2.1M | 3.4-3.5s | 5.8-6.1s | 340K-360K/s |
| ~35 MB | 95K | 3.7M | 4.4-5.6s | 8.2-8.5s | 435K-448K/s |

**Key Insight:** Both implementations call the same C++ parsing function. Python's ProcessPoolExecutor achieves better parallel efficiency through true multiprocessing, making Python the recommended interface for all use cases.

---

# **C++ Usage Example**

**Single File Processing:**

```cpp
// stdf_measurement_extraction_example.cpp
#include "cpp/include/ultra_fast_processor.h"

int main() {
    UltraFastProcessor processor;

    // Process STDF file - returns vector of MeasurementTuple
    auto measurements = processor.process_stdf_file_measurements("test.stdf");

    std::cout << "Extracted " << measurements.size() << " measurements\n";

    // Access tuple fields
    for (const auto& m : measurements) {
        std::cout << "Device: " << m.wld_device_dmc
                  << " Param: " << m.wtp_param_name
                  << " Value: " << m.wptm_value << "\n";
    }
}
```

**Parallel Processing (Multiple Files):**

```cpp
// Process directory with parallel execution
std::vector<std::future<std::pair<size_t, double>>> futures;

for (const auto& file : stdf_files) {
    futures.push_back(std::async(std::launch::async, process_single_file, file));
}

for (auto& future : futures) {
    auto [count, time] = future.get();
    std::cout << count << " measurements in " << time << "s\n";
}
```

**Build:** `g++ -O3 -std=c++14 stdf_measurement_extraction_example.cpp -Lcpp/third_party/lib -lstdf`

---

# **Python Usage Example**

**Single File Processing:**

```python
# extract_all_only_measurements.py
import stdf_parser_cpp

# Process STDF file
result = stdf_parser_cpp.process_stdf_file_measurements("test.stdf")

# Extract measurements and mappings
measurements = result['measurement_tuples']
device_map = result['device_mappings']
param_map = result['param_mappings']

print(f"Extracted {len(measurements)} measurements")
print(f"Found {len(device_map)} devices, {len(param_map)} parameters")

# Access tuple fields (13 fields per tuple)
for m in measurements:
    device_id, param_id, x, y, value, test_flag, segment, \
    file_hash, device_dmc, param_name, units, test_num, test_flg = m
    print(f"{device_dmc} | {param_name} = {value} {units}")
```

**Parallel Processing:**

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def process_file(filepath):
    result = stdf_parser_cpp.process_stdf_file_measurements(filepath)
    return len(result['measurement_tuples'])

# ProcessPoolExecutor for true parallelism (avoids GIL)
with ProcessPoolExecutor(max_workers=3) as executor:
    future_to_file = {executor.submit(process_file, f): f for f in stdf_files}

    total = 0
    for future in as_completed(future_to_file):
        count = future.result()
        total += count
        print(f"{future_to_file[future]}: {count:,} measurements")

    print(f"Total: {total:,} measurements")
```

---

# **Accessing Measurement Data**



| Index | Field | C++ Type | Python Type | Description |
|-------|-------|----------|-------------|-------------|
| 0 | `wld_id` | uint32_t | int | Device numeric ID |
| 1 | `wtp_id` | uint32_t | int | Parameter numeric ID |
| 2 | `wp_pos_x` | int32_t | int | X coordinate (pixel tests) |
| 3 | `wp_pos_y` | int32_t | int | Y coordinate (pixel tests) |
| 4 | `wptm_value` | double | float | Measurement value |
| 5 | `test_flag` | uint8_t | int | Test flag |
| 6 | `segment` | uint8_t | int | Segment identifier |
| 7 | `file_hash` | string | str | File hash |
| 8 | `wld_device_dmc` | string | str | Device DMC string |
| 9 | `wtp_param_name` | string | str | Parameter name |
| 10 | `units` | string | str | Measurement units |
| 11 | `test_num` | uint32_t | int | Test number |
| 12 | `test_flg` | uint8_t | int | Test flag (from PTR/MPR/FTR record) |

**Key Differences:**

- **Python**: Returns tuples (immutable, index or unpack access)
- **C++**: Returns structs (mutable, named field access)
- **Same data**: Both contain identical measurement information
- **Performance**: C++ struct access is slightly faster (direct memory access)
---

**Python: Tuple Structure**

```python
result = stdf_parser_cpp.process_stdf_file_measurements("test.stdf")
measurements = result['measurement_tuples']
for m in measurements:
    # Option 1: Unpack all fields (correct order from measurement_fields.def)
    wld_id, wtp_id, wp_pos_x, wp_pos_y, wptm_value, test_flag, segment, \
    file_hash, wld_device_dmc, wtp_param_name, units, test_num, test_flg = m
    print(f"Device: {wld_device_dmc} (ID: {wld_id})")
    print(f"Parameter: {wtp_param_name} (ID: {wtp_id})")
    print(f"Value: {wptm_value} {units}")
    print(f"Position: X={wp_pos_x}, Y={wp_pos_y}")
    print(f"Test: {test_num}, Flags: test_flag={test_flag}, test_flg={test_flg}") 
    # Option 2: Access by index
    print(f"{m[8]} | {m[9]} = {m[4]} {m[10]}")  # wld_device_dmc | wtp_param_name = wptm_value units
```
**C++: MeasurementTuple Structure**

```cpp
#include "cpp/include/ultra_fast_processor.h"

UltraFastProcessor processor;
auto measurements = processor.process_stdf_file_measurements("test.stdf");

// Each measurement is a MeasurementTuple struct
for (const auto& m : measurements) {
    // Direct field access via struct members (matches measurement_fields.def)
    std::cout << "Device: " << m.wld_device_dmc
              << " (ID: " << m.wld_id << ")\n";
    std::cout << "Parameter: " << m.wtp_param_name
              << " (ID: " << m.wtp_id << ")\n";
    std::cout << "Value: " << m.wptm_value
              << " " << m.units << "\n";
    std::cout << "Position: X=" << m.wp_pos_x
              << ", Y=" << m.wp_pos_y << "\n";
    std::cout << "Test: " << m.test_num
              << ", Flags: test_flag=" << (int)m.test_flag
              << ", test_flg=" << (int)m.test_flg << "\n";
}
```

**C++: MeasurementTuple Field Names (Auto-generated from measurement_fields.def)**

```cpp
struct MeasurementTuple {
    uint32_t wld_id;             // Device numeric ID
    uint32_t wtp_id;             // Parameter numeric ID
    int32_t wp_pos_x;            // X coordinate (pixel tests)
    int32_t wp_pos_y;            // Y coordinate (pixel tests)
    double wptm_value;           // Measurement value
    //...... others
```




---

# **Development Workflow**

**Common Development Tasks:**

<div class="process-box">
<span class="step-number">1</span><strong>Add New Field</strong><br>
Edit <code>.def</code> file → Recompile → Field automatically extracted
</div>

<div class="process-box">
<span class="step-number">2</span><strong>Modify Processing Logic</strong><br>
Edit <code>ultra_fast_processor.cpp</code> → Update cross-product logic → Rebuild
</div>

<div class="process-box">
<span class="step-number">3</span><strong>Debug Parsing Issues</strong><br>
Check <code>stdf_parser.cpp::parse_record()</code> → Verify record type routing → Inspect field extraction
</div>

<br>

**Key Files for Developers:**
- **Field Definitions:** `cpp/field_defs/*.def`
- **Parser Core:** `cpp/src/stdf_parser.cpp`
- **Field Extraction:** `cpp/src/dynamic_field_extractor.cpp`
- **Measurement Logic:** `cpp/src/ultra_fast_processor.cpp`
- **Python Bridge:** `cpp/src/python_bridge.cpp`

---

# **Summary: Developer Quick Reference**

**Architecture Layers:**
- **libstdf** - Binary parsing, compression, byte order
- **STDFParser** - Record routing, type safety, file management
- **X-Macros** - Dynamic field extraction from .def files
- **UltraFastProcessor** - Measurement creation, ID mapping

**Performance:**
- Single file: 3-6 seconds for 30-35 MB files (340K-448K measurements/sec)
- Parallel (Python): 177 MB (6 files, 17.3M measurements) in 20.29 seconds
- Parallel speedup: 3.3x with ProcessPoolExecutor (Python) or std::async (C++)

**Usage:**
- **Recommended:** Python interface via `stdf_parser_cpp` module
- **Alternative:** C++ direct API via `UltraFastProcessor::process_stdf_file_measurements()`

**Extending the Parser:**
- Add field: Edit `.def` file (1 line)
- New record type: Create `.def` + template specialization
- Modify logic: Edit `ultra_fast_processor.cpp`

**Key Advantage:** X-Macro system means most changes require editing data files, not writing new code!