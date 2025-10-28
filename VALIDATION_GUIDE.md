# TSR Record Extraction Validation Guide

## Overview

The TSR validation system ensures that TSR records are properly extracted from STDF files with all expected fields. This is critical for validating that the parser correctly handles TSR record types after they are added or modified.

## Validation Script

**Location:** `scripts/validate_tsr_extraction.py`

This script validates:
1. **TSR Records Exist** - Checks that TSR records are present in parsed data
2. **Required Fields Present** - Validates that all expected fields are extracted
3. **Field Count Validation** - Ensures minimum record count thresholds are met

## Usage

### Basic Usage

```bash
# Validate TSR records exist (minimal check)
python scripts/validate_tsr_extraction.py

# Validate with specific required fields
python scripts/validate_tsr_extraction.py --required-fields "TEST_NUM,TEST_TYP,EXEC_CNT"

# Validate with minimum record count
python scripts/validate_tsr_extraction.py --min-records 1000

# Show detailed output
python scripts/validate_tsr_extraction.py --verbose

# Specify custom STDF file
python scripts/validate_tsr_extraction.py path/to/file.stdf
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `stdf_file` | Path to STDF file to validate | Test file in `STDF_Files/` |
| `--required-fields` | Comma-separated list of required field names | None (only checks TSR exists) |
| `--min-records` | Minimum number of TSR records expected | 1 |
| `--verbose` | Show detailed output including sample records | False |
| `--no-color` | Disable colored output | False (auto-disabled on Windows) |

### Exit Codes

- **0** - All validations passed ✅
- **1** - Validation failed (TSR missing or required fields not found) ❌

## CI/CD Integration

The validation script is integrated into the GitHub Actions workflow at two key points:

### Phase 3 Validation (After Initial Build)

```yaml
- name: Phase 3 - Validate TSR Extraction (Initial)
  run: |
    # Validates TSR records exist with basic fields
    python scripts/validate_tsr_extraction.py \
      --no-color \
      --required-fields "HEAD_NUM,SITE_NUM,TEST_NUM,RECORD_TYPE" \
      --min-records 1000
```

**Expected Result:** TSR records found with 4+ basic fields

### Phase 6 Validation (After Field Modification)

```yaml
- name: Phase 6 - Validate TSR Extraction (After Modification)
  run: |
    # Validates all 15 added TSR fields are extracted
    python scripts/validate_tsr_extraction.py \
      --no-color \
      --required-fields "TEST_TYP,TEST_NUM,EXEC_CNT,FAIL_CNT,ALRM_CNT,TEST_NAM,SEQ_NAME,TEST_LBL,OPT_FLAG,TEST_TIM,TEST_MIN,TEST_MAX,TST_SUMS,TST_SQRS" \
      --min-records 1000
```

**Expected Result:** TSR records found with all 15 modified fields

## Example Output

### Successful Validation

```
================================================================================
TSR RECORD EXTRACTION VALIDATOR
================================================================================

Parsing STDF file...
  File: OSBE25_KEWGBBMD1U_BE_HRG39021_KEWGBBMD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5215_4_20241017193900.stdf
  Size: 33.47 MB

================================================================================
TSR EXTRACTION VALIDATION RESULTS
================================================================================

Parsing Summary:
  Total records parsed: 213,608
  Record types found: 8
  Record types: FTR, HBR, MIR, MPR, PRR, PTR, SBR, TSR

TSR Record Check:
  ✓ PASSED - TSR records found
    TSR record count: 118,665
    Percentage of total: 55.6%

TSR Field Extraction:
  Total fields extracted: 19
  Fields: ALRM_CNT, EXEC_CNT, FAIL_CNT, HEAD_NUM, OPT_FLAG, RECORD_TYPE, REC_SUB, REC_TYPE, SEQ_NAME, SITE_NUM, TEST_LBL, TEST_MAX, TEST_MIN, TEST_NAM, TEST_NUM, TEST_TIM, TEST_TYP, TST_SQRS, TST_SUMS

Required Field Validation:
  Required fields: 15
  Fields: TEST_TYP, TEST_NUM, EXEC_CNT, FAIL_CNT, ALRM_CNT, TEST_NAM, SEQ_NAME, TEST_LBL, OPT_FLAG, TEST_TIM, TEST_MIN, TEST_MAX, TST_SUMS, TST_SQRS

  ✓ PASSED - All required fields present

================================================================================
VALIDATION SUMMARY
================================================================================

  ✓ TSR records found: Found 118,665 TSR records
  ✓ Required fields: All 19 fields extracted successfully

🎉 ALL VALIDATIONS PASSED!
```

### Failed Validation (Missing Fields)

```
================================================================================
TSR EXTRACTION VALIDATION RESULTS
================================================================================

TSR Record Check:
  ✓ PASSED - TSR records found
    TSR record count: 118,665

TSR Field Extraction:
  Total fields extracted: 6
  Fields: HEAD_NUM, RECORD_TYPE, REC_SUB, REC_TYPE, SITE_NUM, TEST_NUM

Required Field Validation:
  Required fields: 15

  ✗ FAILED - Missing 9 required fields
    Missing: ALRM_CNT, EXEC_CNT, FAIL_CNT, OPT_FLAG, SEQ_NAME, TEST_LBL, TEST_MAX, TEST_MIN, TEST_NAM

================================================================================
VALIDATION SUMMARY
================================================================================

  ✓ TSR records found: Found 118,665 TSR records
  ✗ Required fields: Missing 9 required fields

❌ VALIDATION FAILED!
```

## Workflow Phases

The validation system is part of a 7-phase CI/CD workflow:

1. **Phase 1** - Add TSR Record Type
   - Adds TSR to record type registry
   - Creates TSR field definition file

2. **Phase 2** - Build C++ Extension (Initial)
   - Compiles parser with TSR support

3. **Phase 3** - Test TSR Record Extraction (Initial)
   - Runs demo parser
   - **✅ VALIDATION: TSR records exist with basic fields**

4. **Phase 4** - Modify TSR Field Definitions
   - Adds 15 additional TSR fields to definition file

5. **Phase 5** - Rebuild C++ Extension (After Modification)
   - Recompiles with modified field definitions

6. **Phase 6** - Test TSR Record Extraction (After Modification)
   - Runs demo parser with modified fields
   - **✅ VALIDATION: All 15 TSR fields extracted correctly**

7. **Phase 7** - Cleanup & Summary
   - Restores original state
   - Prints summary

## TSR Field Reference

### Basic Fields (Phase 3)

These fields are available immediately after TSR is added:

| Field | Description |
|-------|-------------|
| `HEAD_NUM` | Test head number |
| `SITE_NUM` | Test site number |
| `TEST_NUM` | Test number |
| `RECORD_TYPE` | Record type identifier (TSR) |
| `REC_SUB` | Record sub-type |
| `REC_TYPE` | Record type code |

### Extended Fields (Phase 6)

Additional fields added in Phase 4:

| Field | Description |
|-------|-------------|
| `TEST_TYP` | Test type (F/P for functional/parametric) |
| `EXEC_CNT` | Execution count |
| `FAIL_CNT` | Fail count |
| `ALRM_CNT` | Alarm count |
| `TEST_NAM` | Test name |
| `SEQ_NAME` | Sequence name |
| `TEST_LBL` | Test label |
| `OPT_FLAG` | Optional data flag |
| `TEST_TIM` | Test time |
| `TEST_MIN` | Test minimum value |
| `TEST_MAX` | Test maximum value |
| `TST_SUMS` | Test sum |
| `TST_SQRS` | Test sum of squares |

## Troubleshooting

### Issue: "Could not import stdf_parser_cpp"

**Solution:** Build the C++ extension first:
```bash
python setup_windows_mingw.py build_ext --inplace
```

### Issue: "TSR records NOT FOUND"

**Possible Causes:**
1. TSR record type not added to registry
2. C++ extension not rebuilt after adding TSR
3. STDF file doesn't contain TSR records

**Solution:**
```bash
# Add TSR record type
python scripts/add_record_type.py TSR rec_tsr 10 30

# Rebuild extension
python setup_windows_mingw.py build_ext --inplace
```

### Issue: "Missing required fields"

**Possible Causes:**
1. Field definitions not added to `tsr_fields.def`
2. C++ extension not rebuilt after modifying fields
3. Field names don't match libstdf structure

**Solution:**
```bash
# Add fields to cpp/field_defs/tsr_fields.def
# Example:
# FIELD("TEST_TYP", TEST_TYP)
# FIELD("TEST_NUM", TEST_NUM)

# Rebuild extension
python setup_windows_mingw.py build_ext --inplace --force
```

## Local Testing

To test the validation system locally before pushing to CI/CD:

```bash
# 1. Add TSR record type
python scripts/add_record_type.py TSR rec_tsr 10 30

# 2. Build extension
python setup_windows_mingw.py build_ext --inplace

# 3. Run initial validation
python scripts/validate_tsr_extraction.py \
  --required-fields "HEAD_NUM,SITE_NUM,TEST_NUM,RECORD_TYPE" \
  --min-records 1000 \
  --verbose

# 4. Modify TSR fields (add to cpp/field_defs/tsr_fields.def)
# ... edit file ...

# 5. Rebuild
python setup_windows_mingw.py build_ext --inplace --force

# 6. Run full validation
python scripts/validate_tsr_extraction.py \
  --required-fields "TEST_TYP,TEST_NUM,EXEC_CNT,FAIL_CNT,ALRM_CNT,TEST_NAM,SEQ_NAME,TEST_LBL,OPT_FLAG,TEST_TIM,TEST_MIN,TEST_MAX,TST_SUMS,TST_SQRS" \
  --min-records 1000 \
  --verbose
```

## Integration with Other Scripts

The validation script works alongside:

- **`demo_parser.py`** - Provides human-readable output for all record types
- **`test_field_extraction.py`** - Tests field extraction for specific record types
- **`scripts/add_record_type.py`** - Adds new record types (like TSR)

## Contributing

When adding new record types or modifying field definitions:

1. Update field definition files (`cpp/field_defs/*_fields.def`)
2. Rebuild C++ extension
3. Run validation script to verify changes
4. Update CI/CD workflow if validation criteria change

## See Also

- [Main README](README.md) - Project overview
- [scripts/add_record_type.py](scripts/add_record_type.py) - Record type addition tool
- [demo_parser.py](demo_parser.py) - Demo parser with auto-detection
- [.github/workflows/main.yml](.github/workflows/main.yml) - CI/CD workflow
