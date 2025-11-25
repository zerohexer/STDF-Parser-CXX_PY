# Directory Hierarchy Comparison

## Your Question
> "STDF filenames already contain metadata. Should we use subdirectories or not?"

## Answer: Use **Simplified Hierarchy** ⭐

Your filenames already have all metadata:
```
OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225947.stdf
```

So a **deep 4-level hierarchy is redundant**. Use a **simpler 2-level hierarchy** instead.

---

## Two Approaches Available

### Approach 1: **Simplified Hierarchy** (RECOMMENDED) ⭐

**File:** `watchdog_ingestion_simple.py`

**Structure:**
```
incoming/
├── OSBE25/                    # Level 1: Facility
│   ├── 2024-09-03/           # Level 2: Date
│   │   └── OSBE25_KEWGBCLD1U_...20240903225947.stdf
│   └── 2024-09-04/
│       └── OSBE25_KEWGBCLD1U_...20240904091234.stdf
└── OSBE26/
    └── 2024-09-03/
        └── OSBE26_LOT002_...20240903151020.stdf
```

**Metadata Source:** Parsed from **filename** (single source of truth)

**Advantages:**
- ✅ Simple: Only 2 directory levels
- ✅ Flexible: Works with any filename variations
- ✅ No conflicts: Filename is authoritative
- ✅ Natural: Matches your existing naming convention
- ✅ Date auto-extracted from filename timestamp

**Usage:**
```bash
python watchdog_ingestion_simple.py --hierarchy facility-date
```

---

### Approach 2: **Deep Hierarchy** (Original Design)

**File:** `watchdog_ingestion.py`

**Structure:**
```
incoming/
├── OSBE25/                    # Level 1: Facility
│   └── KEWGBCLD1U/           # Level 2: Lot
│       └── BE_HRG3301Y.06/   # Level 3: Product
│           └── Prod_TPP202_03/  # Level 4: Test Program
│               └── *.stdf
```

**Metadata Source:** Parsed from **directory path**

**Advantages:**
- ✅ Visual organization in file browser
- ✅ Easy to find files by browsing
- ✅ Explicit structure

**Disadvantages:**
- ⚠️ Redundant: Filename already has this info
- ⚠️ Complex: 4 directory levels to manage
- ⚠️ Conflict risk: Directory vs filename mismatch
- ⚠️ Rigid: Hard to handle variations

**Usage:**
```bash
python watchdog_ingestion.py --base-path /data/stdf-ingestion
```

---

## Side-by-Side Comparison

| Aspect | Simplified (facility-date) | Deep (facility/lot/product/program) |
|--------|----------------------------|-------------------------------------|
| **Levels** | 2 (FACILITY/DATE) | 4 (FACILITY/LOT/PRODUCT/PROGRAM) |
| **Metadata From** | Filename parsing | Directory structure |
| **Complexity** | ⭐⭐⭐ Simple | ⚠️ Complex |
| **Flexibility** | ⭐⭐⭐ High | ⚠️ Rigid |
| **Your Use Case** | ✅ Perfect fit | ⚠️ Redundant |
| **File Placement** | `OSBE25/2024-09-03/file.stdf` | `OSBE25/LOT/PROD/PROG/file.stdf` |
| **Script** | `watchdog_ingestion_simple.py` | `watchdog_ingestion.py` |

---

## Hierarchy Options (Simplified Approach)

The simplified watchdog offers **3 hierarchy modes**:

### 1. **facility-date** (Recommended) ⭐
```
incoming/OSBE25/2024-09-03/file.stdf
         └─────┘ └────────┘
         FACILITY  DATE (from filename)
```

### 2. **facility** (Simpler)
```
incoming/OSBE25/file.stdf
         └─────┘
         FACILITY
```

### 3. **flat** (Simplest, testing only)
```
incoming/file.stdf
```

---

## Example: Same File, Different Hierarchies

**Your filename:**
```
OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225947.stdf
```

### Simplified Hierarchy (facility-date)
```
incoming/OSBE25/2024-09-03/OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_...20240903225947.stdf
         └─────┘ └────────┘ └────────────────────────────────────────────────────┘
         FACILITY  DATE      METADATA IN FILENAME (parsed by watchdog)
```

### Deep Hierarchy
```
incoming/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03/OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_...stdf
         └─────┘ └────────┘ └────────────┘ └────────────┘ └──────────────────────────────────┘
         DIR      DIR        DIR            DIR            METADATA DUPLICATED IN FILENAME
         (redundant with filename metadata)
```

Notice how the deep hierarchy **duplicates** what's already in the filename!

---

## Recommendation

**Use the Simplified Hierarchy** with `facility-date` mode:

```bash
# Setup (creates OSBE25/, OSBE26/ directories)
mkdir -p /data/stdf-ingestion/incoming/{OSBE25,OSBE26}

# Start watchdog
python watchdog_ingestion_simple.py --hierarchy facility-date

# Copy files (date folders auto-created from filename timestamp)
cp OSBE25_*.stdf /data/stdf-ingestion/incoming/OSBE25/
cp OSBE26_*.stdf /data/stdf-ingestion/incoming/OSBE26/
```

Watchdog will:
1. ✅ Parse facility from filename → Route to correct facility directory
2. ✅ Parse timestamp from filename → Create/use date subdirectory
3. ✅ Extract all metadata (lot, product, program, tester, temp, etc.)
4. ✅ Process and push to ClickHouse
5. ✅ Archive in `processed/FACILITY/DATE/YYYY/MM/DD/`

---

## Why Simplified is Better for Your Use Case

| Reason | Explanation |
|--------|-------------|
| **Filename has metadata** | Your filenames already contain facility, lot, product, program - don't duplicate in directories |
| **Single source of truth** | Filename is authoritative, not directory structure |
| **Simpler management** | 2 levels vs 4 levels to create/maintain |
| **No conflicts** | Can't have mismatch between directory name and filename |
| **Natural fit** | Matches your existing file naming convention |
| **Flexible** | Easy to handle filename variations without changing directory structure |

---

## When to Use Deep Hierarchy

Use the deep hierarchy (`watchdog_ingestion.py`) when:

❌ Filenames **don't** contain metadata (e.g., `test1.stdf`, `test2.stdf`)
❌ Need visual organization in file browser
❌ Multiple sources provide files with inconsistent naming
❌ Directory structure is dictated by external system

**But for your case**: Filenames already have metadata, so simplified is better! ✅

---

## Quick Decision Guide

```
Does your filename have FACILITY_LOT_PRODUCT_PROGRAM?
│
├─ YES → Use watchdog_ingestion_simple.py (facility-date mode) ⭐
│         Simple, flexible, no redundancy
│
└─ NO  → Use watchdog_ingestion.py (deep hierarchy)
          Organize files by directory structure
```

**Your case:** YES → Use `watchdog_ingestion_simple.py`! ⭐

---

## Files Provided

| File | Purpose | When to Use |
|------|---------|-------------|
| **watchdog_ingestion_simple.py** | Filename-based parsing, simple hierarchy | Your use case ⭐ |
| **watchdog_ingestion.py** | Directory-based metadata, deep hierarchy | Files without metadata |
| **SIMPLE_HIERARCHY_GUIDE.md** | Guide for simplified approach | Read this first ⭐ |
| **WATCHDOG_INGESTION_README.md** | Guide for deep hierarchy | Reference |
| **DIRECTORY_STRUCTURE_REFERENCE.txt** | Visual reference for deep hierarchy | Reference |

---

## Bottom Line

**Use `watchdog_ingestion_simple.py` with `--hierarchy facility-date`**

It's simpler, matches your filename convention, and avoids redundancy! 🚀

```bash
python watchdog_ingestion_simple.py --hierarchy facility-date
```
