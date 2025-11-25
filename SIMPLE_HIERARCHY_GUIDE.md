# STDF Watchdog - Simplified Hierarchy Guide

Since your STDF filenames **already contain all metadata**, you don't need a deep directory hierarchy!

## Your Filename Format

```
OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225947.stdf
└────┘ └─────────┘ └──────────────┘                      └─────────────┘ └────────┘ └──┘ └────┘ └────────────┘
FACILITY   LOT        PRODUCT                            TEST_PROGRAM   TESTER    TEMP  SEQ   TIMESTAMP
```

All metadata is **parsed from the filename**, so directory structure is just for **organization**, not data extraction.

---

## Three Hierarchy Options

### Option 1: **Facility + Date** (Recommended) ⭐

```
incoming/
├── OSBE25/
│   ├── 2024-09-03/
│   │   └── OSBE25_KEWGBCLD1U_...20240903225947.stdf
│   │   └── OSBE25_KEWGBCLD1U_...20240903230102.stdf
│   └── 2024-09-04/
│       └── OSBE25_KEWGBCLD1U_...20240904091234.stdf
└── OSBE26/
    └── 2024-09-03/
        └── OSBE26_LOT002_...20240903151020.stdf
```

**Why this is best:**
- ✅ Organizes by facility (multi-site support)
- ✅ Date-based folders prevent millions of files in one directory
- ✅ Easy to find files from specific dates
- ✅ Date extracted automatically from filename timestamp
- ✅ Good filesystem performance

**Usage:**
```bash
python watchdog_ingestion_simple.py --hierarchy facility-date
```

---

### Option 2: **Facility Only** (Simpler)

```
incoming/
├── OSBE25/
│   └── OSBE25_KEWGBCLD1U_...20240903225947.stdf
│   └── OSBE25_KEWGBCLD1U_...20240903230102.stdf
│   └── OSBE25_KEWGBCLD1U_...20240904091234.stdf (all files together)
└── OSBE26/
    └── OSBE26_LOT002_...20240903151020.stdf
```

**Why use this:**
- ✅ Simple organization by facility
- ✅ Easy to route files per site
- ⚠️ Could get crowded with many files per facility

**Usage:**
```bash
python watchdog_ingestion_simple.py --hierarchy facility
```

---

### Option 3: **Flat** (Simplest but risky)

```
incoming/
└── OSBE25_KEWGBCLD1U_...20240903225947.stdf
└── OSBE25_KEWGBCLD1U_...20240903230102.stdf
└── OSBE26_LOT002_...20240903151020.stdf (all files in one place)
```

**Why use this:**
- ✅ Dead simple - just drop files anywhere
- ✅ No directory coordination needed
- ⚠️ **Performance issues** with millions of files
- ⚠️ Hard to browse/navigate

**Usage:**
```bash
python watchdog_ingestion_simple.py --hierarchy flat
```

---

## Comparison

| Hierarchy | Directories | Files per Dir | Performance | Best For |
|-----------|-------------|---------------|-------------|----------|
| **facility-date** | Many (FACILITY/DATE) | 100s-1000s | ⭐⭐⭐ Excellent | **Production (Recommended)** |
| **facility** | Few (FACILITY) | 1000s-10000s | ⭐⭐ Good | Medium-scale operations |
| **flat** | One | Unlimited | ⚠️ Poor (millions) | Testing/dev only |

---

## Quick Start

### 1. Choose Your Hierarchy

```bash
# Recommended: Facility + Date
python watchdog_ingestion_simple.py --hierarchy facility-date

# OR: Facility only
python watchdog_ingestion_simple.py --hierarchy facility

# OR: Flat (testing only)
python watchdog_ingestion_simple.py --hierarchy flat
```

### 2. Copy Files to Incoming

**For facility-date:**
```bash
# Watchdog auto-creates date folders based on filename timestamp
cp OSBE25_KEWGBCLD1U_...20240903225947.stdf /data/stdf-ingestion/incoming/OSBE25/2024-09-03/

# OR just drop in facility folder, watchdog will organize
cp *.stdf /data/stdf-ingestion/incoming/OSBE25/
```

**For facility:**
```bash
cp OSBE25_*.stdf /data/stdf-ingestion/incoming/OSBE25/
cp OSBE26_*.stdf /data/stdf-ingestion/incoming/OSBE26/
```

**For flat:**
```bash
cp *.stdf /data/stdf-ingestion/incoming/
```

---

## What Gets Extracted from Filename

The parser automatically extracts:

| Field | Example | Used For |
|-------|---------|----------|
| **Facility** | `OSBE25` | Site identification |
| **Lot** | `KEWGBCLD1U` | Production lot |
| **Product** | `BE_HRG3301Y.06` | Device/product type |
| **Test Program** | `Prod_TPP202_03` | Test program name |
| **Tester** | `Agilent_93000MT9510` | Equipment ID |
| **Temperature** | `25C` | Test temperature |
| **Sequence** | `5264_2` | File sequence |
| **Timestamp** | `20240903225947` | Test date/time |
| **Date** | `2024-09-03` | Derived from timestamp |

All of this goes into ClickHouse with data from the STDF file itself.

---

## Filename Validation

The watchdog validates filenames match this pattern:

```
{FACILITY}_{LOT}_{PRODUCT}_{LOT}_{PROGRAM}_{TESTER}_{TEMP}_{SEQ}_{TIMESTAMP}.stdf
```

If a file doesn't match:
- ⚠️ Warning logged
- ✅ Still processes the file
- 🏷️ Uses `UNKNOWN` for missing metadata fields

---

## Example Workflow

### Facility-Date Mode (Recommended)

```bash
# 1. Start watchdog
python watchdog_ingestion_simple.py --hierarchy facility-date

# 2. Copy files (watchdog detects based on timestamp in filename)
cp OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_...20240903225947.stdf \
   /data/stdf-ingestion/incoming/OSBE25/2024-09-03/

# 3. Watchdog automatically:
#    - Validates filename format
#    - Extracts metadata (OSBE25, KEWGBCLD1U, BE_HRG3301Y.06, Prod_TPP202_03, etc.)
#    - Moves to processing/OSBE25/2024-09-03/
#    - Parses STDF file
#    - Pushes to ClickHouse
#    - Moves to processed/OSBE25/2024-09-03/2025/11/24/ (archive date)

# 4. Check results
find /data/stdf-ingestion/processed -name "*.stdf"
```

---

## Migration from Deep Hierarchy

If you already created the deep 4-level hierarchy, it's easy to switch:

```bash
# Stop old watchdog
kill <old-watchdog-pid>

# Start new simplified watchdog
python watchdog_ingestion_simple.py --hierarchy facility-date

# Move existing files to new structure
cd /data/stdf-ingestion/incoming
for f in OSBE25/*/*/*/*.stdf; do
    # Extract date from filename timestamp
    # Move to OSBE25/YYYY-MM-DD/
done
```

Or just start fresh - both approaches work with the same filenames!

---

## Advantages Over Deep Hierarchy

✅ **Simpler**: 2 levels (facility/date) vs 4 levels (facility/lot/product/program)
✅ **Flexible**: Handles variations in filename format
✅ **Single Source of Truth**: Filename is authoritative, not directory structure
✅ **No Mismatch Issues**: Can't have directory saying "LOT001" but filename saying "LOT002"
✅ **Natural**: Matches how your files are already named
✅ **Future-proof**: Easy to add new metadata fields to filename without changing directories

---

## When to Use Each Approach

| Use Case | Recommended Hierarchy |
|----------|----------------------|
| **Production, multiple sites** | `facility-date` ⭐ |
| **Single site, moderate volume** | `facility` |
| **Testing/development** | `flat` |
| **Filenames don't have metadata** | Deep hierarchy (original design) |
| **Filenames HAVE metadata** | Simple hierarchy (this design) ⭐ |

---

## Summary

**Your filenames already have all the metadata**, so use a **simple hierarchy** for organization:

```bash
# Recommended command:
python watchdog_ingestion_simple.py \
    --hierarchy facility-date \
    --clickhouse-host localhost \
    --clickhouse-port 9000
```

Then just copy files to `incoming/{FACILITY}/{DATE}/` and watchdog does the rest! 🚀

---

## Files

- **watchdog_ingestion_simple.py** - Simplified watchdog with filename parsing
- **watchdog_ingestion.py** - Original deep-hierarchy version (still works!)

Both scripts are available - choose based on your preference! The simplified version is recommended for your use case.
