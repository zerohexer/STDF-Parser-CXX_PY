# State Management Guide - Avoiding Reprocessing

## Your Questions Answered ✅

### Q1: "Should we monitor main top folder?"

**YES! Monitor the TOP level (parent of OSBE25) with `recursive=True`**

```python
# Monitor incoming/ directory recursively
observer.schedule(event_handler, "/data/stdf-ingestion/incoming", recursive=True)
```

```
/data/stdf-ingestion/incoming/    ← MONITOR HERE (recursive)
├── OSBE25/                        ← Auto-detected
│   ├── KEWGBCLD1U/               ← Auto-detected
│   │   └── HRG3301Y.06/          ← Auto-detected
│   │       └── Prod_TPP202_03/   ← Auto-detected
│   │           └── file.stdf     ← DETECTED!
├── OSBE26/                        ← Auto-detected
└── OSBE27/                        ← Auto-detected (dynamic!)
```

**Benefits:**
- ✅ Single watcher for ALL facilities (OSBE25, OSBE26, OSBE27, ...)
- ✅ Auto-detects new facilities without configuration
- ✅ Detects files at any depth
- ✅ Scalable

---

### Q2: "How do we keep state on which folder already processed?"

**Two-layer approach (Hybrid):**

#### Layer 1: **File Movement** (Primary State)

```
incoming/OSBE25/.../file.stdf  ← NEW (not processed)
    ↓
processing/OSBE25/.../file.stdf  ← CURRENTLY PROCESSING
    ↓
processed/OSBE25/.../file.stdf  ← DONE (processed)
```

**How it works:**
- Watchdog only triggers on files in `incoming/`
- Once moved to `processing/`, no longer in `incoming/`
- After processing, moved to `processed/` or `failed/`
- **Physical file location = processing state**

**Advantages:**
- ✅ Simple and reliable
- ✅ File presence indicates state
- ✅ No database queries needed for state
- ✅ Watchdog automatically ignores files outside `incoming/`

---

#### Layer 2: **Database Hash Tracking** (Duplicate Detection)

```sql
CREATE TABLE processed_files (
    file_hash String,           -- SHA256 of file content
    file_name String,
    facility String,
    lot String,
    product String,
    test_program String,
    processed_date DateTime,
    status String              -- 'processing', 'completed', 'failed'
) ENGINE = MergeTree()
ORDER BY (facility, processed_date);
```

**How it works:**
```python
# Before processing
file_hash = calculate_hash(file_path)

if file_hash in processed_hashes:
    # DUPLICATE! Already processed this exact file before
    move_to_duplicates_folder(file_path)
    return  # Skip processing
```

**Advantages:**
- ✅ Detects **exact duplicates** (same file copied twice with different names)
- ✅ Prevents wasting resources reprocessing identical data
- ✅ History tracking (when was file processed?)
- ✅ Audit trail

---

### Q3: "If STDF already there, no need to process?"

**YES! Here's how we handle it:**

#### Scenario 1: File Already in `processed/` or `failed/`

```
incoming/OSBE25/.../file.stdf  → Copy new file here
processed/OSBE25/.../file.stdf → Same file already exists here
```

**What happens:**
- ✅ Watchdog detects file in `incoming/`
- ✅ Calculate file hash: `abc123...`
- ✅ Check database: Hash `abc123...` already processed
- ✅ **SKIP PROCESSING** - Move to `duplicates/` folder
- ✅ Log: "Duplicate detected"

**Result:** No reprocessing! ✅

---

#### Scenario 2: Same File, Different Location

```
incoming/OSBE25/LOT001/.../file.stdf     → Processed yesterday
incoming/OSBE26/LOT002/.../file.stdf     → Same file copied today
```

**What happens:**
- ✅ File hash is identical (same content)
- ✅ Database says: "Hash already processed"
- ✅ **SKIP PROCESSING** - Move to `duplicates/`

**Result:** No reprocessing even across different facilities! ✅

---

#### Scenario 3: Different File, Same Name

```
incoming/OSBE25/.../test.stdf  → Processed yesterday (hash: abc123)
incoming/OSBE25/.../test.stdf  → New file today (hash: xyz789, different content)
```

**What happens:**
- ✅ File name is same, but hash is different
- ✅ Database check: Hash `xyz789` NOT processed before
- ✅ **PROCESS NORMALLY** - This is a new file!

**Result:** Correctly processes new file! ✅

---

## Complete State Flow Diagram

```
[User copies file to incoming/]
         ↓
    ┌────────────────────────────┐
    │ Watchdog detects new file  │
    │ (on_created event)         │
    └────────────────────────────┘
         ↓
    ┌────────────────────────────┐
    │ Wait for file stability    │
    │ (ensure complete write)    │
    └────────────────────────────┘
         ↓
    ┌────────────────────────────┐
    │ Calculate file hash        │
    │ SHA256(file content)       │
    └────────────────────────────┘
         ↓
    ┌────────────────────────────┐
    │ Check: Hash processed?     │
    │ Query: processed_files     │
    └────────────────────────────┘
         ↓
         ├─ YES (duplicate) ──→ Move to duplicates/ ──→ DONE ✅
         │
         └─ NO (new file)
              ↓
         ┌────────────────────────────┐
         │ Mark as 'processing' in DB │
         └────────────────────────────┘
              ↓
         ┌────────────────────────────┐
         │ Move to processing/        │
         └────────────────────────────┘
              ↓
         ┌────────────────────────────┐
         │ Parse STDF file            │
         │ Extract measurements       │
         └────────────────────────────┘
              ↓
         ┌────────────────────────────┐
         │ Push to ClickHouse         │
         │ (4 tables)                 │
         └────────────────────────────┘
              ↓
              ├─ SUCCESS ──→ Mark 'completed' in DB ──→ Move to processed/ ──→ DONE ✅
              │
              └─ FAILURE ──→ Mark 'failed' in DB ──→ Move to failed/ + .error.log ──→ DONE ❌
```

---

## Directory States

| Directory | State | Meaning |
|-----------|-------|---------|
| **incoming/** | Not processed | New files, waiting for processing |
| **processing/** | Currently processing | Parser is working on this file |
| **processed/** | Completed | Successfully parsed and inserted to ClickHouse |
| **failed/** | Failed | Parsing or insertion error (see .error.log) |
| **duplicates/** | Duplicate | Already processed before (same hash) |

---

## State Tracking Methods Comparison

| Method | How It Works | Pros | Cons |
|--------|--------------|------|------|
| **File Movement** | Physical file location | ✅ Simple<br>✅ No DB needed<br>✅ Reliable | ⚠️ Can't detect duplicates with different names |
| **Database Hash** | SHA256 in processed_files table | ✅ Detects exact duplicates<br>✅ Audit trail<br>✅ Query history | ⚠️ Requires DB connection |
| **Hybrid (Both)** ⭐ | File movement + hash tracking | ✅ Best of both worlds<br>✅ No reprocessing<br>✅ Duplicate detection | Slightly more complex |

**We use: Hybrid (Both)** ⭐

---

## File Hash Calculation

```python
import hashlib

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file content"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks (handles large files)
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Example
hash1 = calculate_file_hash("incoming/OSBE25/.../file.stdf")
# → "abc123def456..." (unique fingerprint)

# Same file, different name
hash2 = calculate_file_hash("incoming/OSBE26/.../different_name.stdf")
# → "abc123def456..." (SAME hash = duplicate!)
```

**Hash is based on file CONTENT, not name or location!**

---

## Database Schema

```sql
CREATE TABLE processed_files (
    file_hash String,              -- SHA256 hash (primary deduplication key)
    file_name String,              -- Original filename
    file_path String,              -- Full path where processed
    facility String,               -- OSBE25, OSBE26, etc.
    lot String,                    -- LOT001, KEWGBCLD1U, etc.
    product String,                -- HRG3301Y.06, etc.
    test_program String,           -- Prod_TPP202_03, etc.
    file_size_bytes UInt64,        -- File size in bytes
    processed_date DateTime,       -- When processed
    status String,                 -- 'processing', 'completed', 'failed'
    error_message String           -- Error details if failed
) ENGINE = MergeTree()
ORDER BY (facility, processed_date);
```

**Query examples:**

```sql
-- Check if file already processed
SELECT count(*) FROM processed_files
WHERE file_hash = 'abc123def456...' AND status = 'completed';

-- Get processing history for facility
SELECT file_name, processed_date, status
FROM processed_files
WHERE facility = 'OSBE25'
ORDER BY processed_date DESC;

-- Find duplicates
SELECT file_hash, count(*) as cnt
FROM processed_files
GROUP BY file_hash
HAVING cnt > 1;
```

---

## Monitoring Commands

### Check current state:

```bash
# Files waiting to process
find /data/stdf-ingestion/incoming -name "*.stdf" | wc -l

# Files currently processing
find /data/stdf-ingestion/processing -name "*.stdf" | wc -l

# Successfully processed
find /data/stdf-ingestion/processed -name "*.stdf" | wc -l

# Failed processing
find /data/stdf-ingestion/failed -name "*.stdf" | wc -l

# Duplicates detected
find /data/stdf-ingestion/duplicates -name "*.stdf" | wc -l
```

### Check database state:

```sql
-- Total files processed
SELECT count(*) FROM processed_files WHERE status = 'completed';

-- Files by facility
SELECT facility, count(*) FROM processed_files
WHERE status = 'completed'
GROUP BY facility;

-- Recent processing activity
SELECT facility, lot, file_name, processed_date, status
FROM processed_files
ORDER BY processed_date DESC
LIMIT 20;

-- Processing errors
SELECT file_name, error_message, processed_date
FROM processed_files
WHERE status = 'failed'
ORDER BY processed_date DESC;
```

---

## Performance Considerations

### Scanning Strategy

**❌ DON'T: Raw scan all files every time**
```python
# BAD - scans entire directory tree every loop
while True:
    for file in glob.glob("incoming/**/*.stdf", recursive=True):
        if not is_processed(file):  # Expensive check
            process(file)
    time.sleep(60)  # Inefficient!
```

**✅ DO: Use watchdog event-driven monitoring**
```python
# GOOD - only processes NEW files (events)
observer = Observer()
observer.schedule(handler, "incoming/", recursive=True)
observer.start()
# Watchdog calls handler.on_created() only for NEW files!
```

**Benefits:**
- ✅ Instant detection (no polling delay)
- ✅ No wasted CPU scanning unchanged directories
- ✅ Scales to millions of files
- ✅ Event-driven (efficient)

---

### Hash Lookup Performance

**In-memory cache:**
```python
# Load all processed hashes at startup
processed_hashes = set()  # Fast O(1) lookup

def is_processed(file_hash):
    return file_hash in processed_hashes  # Instant!
```

**Performance:**
- 1 million processed files = ~64 MB RAM (hashes only)
- Lookup time: O(1) (instant, regardless of size)
- No database query per file!

---

## Configuration Options

### Option 1: Full State Tracking (Recommended) ⭐

```bash
python watchdog_ingestion_stateful.py
```

- ✅ File movement + database tracking
- ✅ Duplicate detection enabled
- ✅ Full audit trail

### Option 2: File Movement Only (Simple)

```bash
python watchdog_ingestion_stateful.py --no-db-tracking
```

- ✅ File movement only
- ⚠️ No duplicate detection
- ⚠️ No audit trail
- ✅ Simpler (no DB dependency)

---

## Example Scenarios

### Scenario 1: Normal Processing

```bash
# Copy file
cp file.stdf /data/stdf-ingestion/incoming/OSBE25/LOT001/PROD/PROG/

# Watchdog detects → processes → moves to processed/
# Result: processed/OSBE25/LOT001/PROD/PROG/2025/11/24/file.stdf
```

### Scenario 2: Duplicate Detection

```bash
# Copy same file again (already processed)
cp file.stdf /data/stdf-ingestion/incoming/OSBE25/LOT002/PROD/PROG/

# Watchdog detects → hash check → DUPLICATE → moves to duplicates/
# Result: duplicates/OSBE25/LOT002/PROD/PROG/file.stdf
# Log: "DUPLICATE DETECTED: File already processed (hash: abc123...)"
```

### Scenario 3: Processing Error

```bash
# Copy corrupted file
cp corrupted.stdf /data/stdf-ingestion/incoming/OSBE25/.../

# Watchdog detects → tries to parse → ERROR → moves to failed/
# Result: failed/OSBE25/.../corrupted.stdf
#         failed/OSBE25/.../corrupted.error.log (error details)
```

---

## Summary

### Monitoring: **Top Level, Recursive**
```python
observer.schedule(handler, "incoming/", recursive=True)
```
- Detects OSBE25, OSBE26, OSBE27, ... (all facilities)
- Single watcher for entire tree
- Dynamic facility support

### State Tracking: **File Movement + Hash**
1. **File movement**: incoming → processing → processed/failed
2. **Hash tracking**: Database prevents duplicates
3. **Result**: No raw scanning, no reprocessing

### Already Processed? **Skip It!**
- Hash check: Is this file already processed?
- If YES → Move to duplicates/, log, skip
- If NO → Process normally

---

## Quick Start

```bash
# Start watchdog with full state tracking
python watchdog_ingestion_stateful.py \
    --base-path /data/stdf-ingestion \
    --clickhouse-host localhost \
    --clickhouse-port 9000

# Copy files to incoming (any depth)
cp *.stdf /data/stdf-ingestion/incoming/OSBE25/LOT001/PRODUCT/PROGRAM/

# Watchdog automatically:
# 1. Detects new files (event-driven)
# 2. Checks for duplicates (hash lookup)
# 3. Processes new files only
# 4. Moves to processed/ (state tracking)
```

**No raw scanning. No reprocessing. Efficient!** ✅
