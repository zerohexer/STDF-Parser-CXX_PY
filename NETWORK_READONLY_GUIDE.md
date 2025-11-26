# Read-Only Network Folder Monitoring Guide

## Your Scenario

✅ **Network folder** (READ ONLY - can only read, cannot modify)
✅ **Files already exist** there (not being copied, just there)
✅ **Cannot create folders** on network drive (no processing/, failed/, etc.)
✅ Need to **watch and process** without changing network folder

---

## 🎯 Solution Architecture

```
Network Folder (READ ONLY)                    Local Machine
═══════════════════════════                   ═══════════════
/mnt/network/stdf/                            /tmp/stdf-processing/
├── OSBE25/            ←────Watchdog──────→   ├── processing/
│   └── KEWGBCLD1U/         monitors          │   └── temp_file.stdf
│       └── HRG3301Y.06/    (recursive)       ├── failed/
│           └── Prod_TPP202_03/               │   └── error.log
│               ├── file1.stdf (existing)     └── logs/
│               └── file2.stdf (new)              └── ingestion.log
├── OSBE26/
└── OSBE27/

         ↓                                           ↓
         Read files                          Process locally
         (no modify)                         (copy → parse → cleanup)

                           ↓
                    ClickHouse Database
                    ══════════════════
                    processed_files table
                    (tracks what's been processed)
```

---

## 📍 Where Does Watchdog Listen?

### Answer: **Main network folder (parent of OSBE25, OSBE26, etc.)**

```python
# Example network paths
network_path = "/mnt/network/stdf"           # Linux mount point
# OR
network_path = "//server/share/stdf"         # Windows UNC path
# OR
network_path = "./STDF_Files"                # Local testing

# Monitor recursively
observer.schedule(event_handler, network_path, recursive=True)
```

**Structure watchdog monitors:**
```
/mnt/network/stdf/              ← WATCHDOG LISTENS HERE (recursive, read-only)
├── OSBE25/                      ← Auto-detected
│   └── KEWGBCLD1U/             ← Auto-detected
│       └── HRG3301Y.06/        ← Auto-detected
│           └── Prod_TPP202_03/ ← Auto-detected
│               ├── file1.stdf  ← EXISTING FILE (processed on startup)
│               └── file2.stdf  ← NEW FILE (detected by watchdog)
├── OSBE26/                      ← Auto-detected
└── OSBE27/                      ← Auto-detected (dynamic!)
```

---

## 🔄 Processing Flow

```
1. STARTUP: Initial Scan
   ═══════════════════════
   Scan network folder for EXISTING files
   ↓
   For each file:
     Calculate hash → Check database
     ├─ Already processed? → Skip ✅
     └─ New file? → Process ⬇️

2. ONGOING: Watch for New Files
   ═══════════════════════════════
   Watchdog detects new file on network
   ↓
   Calculate hash → Check database
   ├─ Already processed? → Skip ✅
   └─ New file? → Process ⬇️

3. PROCESSING
   ════════════
   Copy to local /tmp/stdf-processing/
   ↓
   Parse STDF (local copy)
   ↓
   Push to ClickHouse
   ↓
   Mark as completed in database
   ↓
   Delete local copy (cleanup)
   ↓
   Network file unchanged (read-only) ✅
```

---

## 🗄️ State Tracking: **Database Only**

Since **cannot move files** on network folder:

### Database = ONLY State Tracker

```sql
CREATE TABLE processed_files (
    file_hash String,              -- SHA256 of file content (PRIMARY KEY for dedup)
    file_path String,              -- Full network path
    file_name String,              -- Filename
    facility String,               -- OSBE25, OSBE26, etc.
    lot String,                    -- LOT001, KEWGBCLD1U, etc.
    product String,                -- HRG3301Y.06, etc.
    test_program String,           -- Prod_TPP202_03, etc.
    file_size_bytes UInt64,        -- File size
    file_modified_time DateTime,   -- Network file's last modified time
    processed_date DateTime,       -- When we processed it
    status String                  -- 'completed' or 'failed'
) ENGINE = MergeTree()
ORDER BY (facility, processed_date);
```

**How it works:**
```python
# Before processing
file_hash = SHA256(network_file)

if file_hash in database.processed_files:
    skip()  # Already processed ✅
else:
    process()  # New file
```

---

## 💾 Local Working Directory

Since **cannot create folders on network**, use **local temp directory**:

```
/tmp/stdf-processing/              (or /data/local-stdf/ for production)
├── processing/
│   └── temp_20241124_153045.stdf  ← Temporary copy for parsing
├── failed/
│   ├── corrupted.stdf             ← Failed files kept locally
│   └── corrupted.error.log        ← Error details
└── logs/
    └── stdf_ingestion_20241124.log ← Daily log file
```

**Advantages:**
- ✅ Network folder **unchanged** (read-only respected)
- ✅ Local processing **fast** (no network I/O during parsing)
- ✅ Failed files **tracked locally** (for debugging)
- ✅ Logs **local** (no network write needed)

---

## 🚀 Usage

### 1. Mount Network Folder (if not already mounted)

**Linux:**
```bash
# CIFS/SMB mount (Windows share)
sudo mount -t cifs //server/share/stdf /mnt/network/stdf -o ro,username=user,password=pass

# NFS mount
sudo mount -t nfs server:/export/stdf /mnt/network/stdf -o ro
```

**Windows:**
```powershell
# Map network drive (read-only)
net use Z: \\server\share\stdf /PERSISTENT:YES
```

**Or for local testing:**
```bash
# Just use local directory
network_path="./STDF_Files"
```

---

### 2. Start Watchdog

```bash
# Production: Network folder
python watchdog_network_readonly.py \
    --network-path /mnt/network/stdf \
    --local-work-dir /data/local-stdf \
    --clickhouse-host localhost \
    --clickhouse-port 9000

# Local testing: Use STDF_Files directory
python watchdog_network_readonly.py \
    --network-path ./STDF_Files \
    --local-work-dir /tmp/stdf-test
```

**What happens:**
1. ✅ Scans existing files in network folder
2. ✅ Processes new files (not in database)
3. ✅ Starts watching for new files
4. ✅ Runs continuously

---

### 3. Skip Initial Scan (optional)

If you only want to process **new files** (not existing ones):

```bash
python watchdog_network_readonly.py \
    --network-path /mnt/network/stdf \
    --skip-initial-scan  ← Skip existing files
```

**Use case:** Already processed all existing files, only want new ones

---

## 📊 Monitoring

### Check Processing Status

```bash
# Files processed today
clickhouse-client --query "
SELECT count(*)
FROM processed_files
WHERE toDate(processed_date) = today() AND status = 'completed'
"

# Files by facility
clickhouse-client --query "
SELECT facility, count(*) as cnt
FROM processed_files
WHERE status = 'completed'
GROUP BY facility
ORDER BY cnt DESC
"

# Recent processing activity
clickhouse-client --query "
SELECT facility, lot, file_name, processed_date, status
FROM processed_files
ORDER BY processed_date DESC
LIMIT 20
"

# Failed files
clickhouse-client --query "
SELECT file_name, error_message, processed_date
FROM processed_files
WHERE status = 'failed'
ORDER BY processed_date DESC
"
```

### Check Local Logs

```bash
# Watch real-time logs
tail -f /tmp/stdf-processing/logs/stdf_ingestion_*.log

# Check for errors
grep -i error /tmp/stdf-processing/logs/*.log

# Count failed files locally
ls -la /tmp/stdf-processing/failed/
```

---

## 🔍 How Files Are Detected

### Existing Files (Initial Scan)

```python
# At startup, scan recursively
for file in network_folder.glob("**/*.stdf"):
    file_hash = calculate_hash(file)

    if file_hash in database:
        print(f"SKIP: {file} (already processed)")
    else:
        process_file(file)
```

**Example output:**
```
Found 1523 existing STDF files
Skipped 1500 (already processed)
Processing 23 new files...
Initial scan complete: 23 processed, 1500 skipped
```

---

### New Files (Watchdog Events)

```python
# Watchdog triggers on new file
def on_created(event):
    if event.src_path.endswith('.stdf'):
        process_network_file(event.src_path)

def on_modified(event):
    # Also trigger on modified (network sync delays)
    if event.src_path.endswith('.stdf'):
        process_network_file(event.src_path)
```

**Why watch `on_modified` too?**
- Network folders may show "modified" instead of "created"
- Syncing delays can trigger modified events
- Handles both cases safely (hash dedup prevents reprocessing)

---

## ✅ Handling Already Processed Files

### Scenario 1: File Already in Database

```bash
# File already processed yesterday
Database: file_hash = "abc123..." → status = 'completed'

# Same file detected again today (network re-scan or restart)
Network: /mnt/network/stdf/OSBE25/.../file.stdf → hash = "abc123..."
```

**What happens:**
1. Calculate hash: `abc123...`
2. Check database: Found! Status = `completed`
3. **SKIP** ✅
4. Log: "Skipped (already processed)"

**No reprocessing!**

---

### Scenario 2: Duplicate Files

```bash
# Same file in different locations
/mnt/network/stdf/OSBE25/LOT001/.../file.stdf → hash: "abc123..."
/mnt/network/stdf/OSBE26/LOT002/.../copy.stdf → hash: "abc123..." (same!)
```

**What happens:**
1. Process first file → Mark hash `abc123...` as completed
2. Detect second file → Calculate hash → `abc123...`
3. Check database → **Already processed!**
4. **SKIP second file** ✅

**Hash-based deduplication works across facilities!**

---

## 🛡️ Safety Features

### 1. File Stability Check

```python
# Wait for file to finish writing (network delays)
wait_for_stable(file_path, timeout=30)

# Check: File size unchanged for 3 consecutive checks
# Prevents reading incomplete files during network transfers
```

### 2. Local Processing (Network Safety)

```python
# Copy to local first
local_copy = copy_to_local(network_file)

# Parse from local (fast, no network I/O)
measurements = parse_stdf(local_copy)

# Network file never locked or modified ✅
```

### 3. Error Handling

```python
try:
    process_file(network_file)
except Exception as e:
    # Save error log locally
    save_error_log(local_failed_dir, error)

    # Mark in database as failed
    database.mark_failed(file_hash, error_message)

    # Network file unchanged ✅
```

---

## 🎯 Network Folder Requirements

### What You Need:

| Requirement | Description |
|-------------|-------------|
| **Read Access** | Can read files, cannot write/modify |
| **Network Mount** | Mounted as local path (e.g., `/mnt/network/stdf`) |
| **Directory Structure** | `FACILITY/LOT/PRODUCT/PROGRAM/*.stdf` |
| **Existing Files** | OK! Processes existing + watches for new |
| **File Format** | `.stdf` files |

### What You DON'T Need:

| Not Required | Reason |
|--------------|--------|
| ❌ Write access | Read-only is fine! |
| ❌ processing/ folder | Created locally instead |
| ❌ failed/ folder | Created locally instead |
| ❌ Modify network files | Files stay unchanged |
| ❌ File movement | State tracked in database |

---

## 📁 Example Directory Structures

### Network Folder (READ ONLY)

```
/mnt/network/stdf/
├── OSBE25/
│   ├── KEWGBCLD1U/
│   │   ├── HRG3301Y.06/
│   │   │   ├── Prod_TPP202_03/
│   │   │   │   ├── file1.stdf (1.2 GB)
│   │   │   │   ├── file2.stdf (980 MB)
│   │   │   │   └── file3.stdf (1.1 GB)
│   │   │   └── Prod_TPP202_04/
│   │   │       └── file4.stdf
│   │   └── PRODUCT_B/
│   │       └── TEST_V1/
│   │           └── file5.stdf
│   └── LOT002/
│       └── ...
├── OSBE26/
│   └── ...
└── OSBE27/
    └── ...
```

### Local Working Directory

```
/tmp/stdf-processing/
├── processing/
│   └── (empty - cleaned after each file)
├── failed/
│   ├── corrupted_20241124_143022.stdf
│   └── corrupted_20241124_143022.error.log
└── logs/
    └── stdf_ingestion_20241124.log
```

---

## 🔄 Complete Processing Example

### Step-by-Step for One File

```bash
# 1. Network file exists
Network: /mnt/network/stdf/OSBE25/KEWGBCLD1U/HRG3301Y.06/Prod_TPP202_03/test.stdf

# 2. Watchdog detects (on startup scan or new file event)
Watchdog: Detected test.stdf

# 3. Calculate hash
Hash: abc123def456... (SHA256 of file content)

# 4. Check database
Database query: SELECT * FROM processed_files WHERE file_hash = 'abc123...'
Result: Not found (new file!)

# 5. Copy to local
Local: /tmp/stdf-processing/processing/test_20241124_153045.stdf

# 6. Parse STDF (local copy)
Parser: Extracted 125,432 measurements

# 7. Push to ClickHouse
ClickHouse: Inserted 125,432 rows into measurements table

# 8. Mark completed in database
Database: INSERT INTO processed_files (file_hash='abc123...', status='completed', ...)

# 9. Cleanup local copy
Local: Delete /tmp/stdf-processing/processing/test_20241124_153045.stdf

# 10. Done!
Network file: UNCHANGED (still at /mnt/network/stdf/.../test.stdf) ✅
Database: Tracked as processed ✅
ClickHouse: Measurements inserted ✅
```

---

## 💡 Best Practices

### 1. Use Fast Local Disk for Processing

```bash
# ❌ Don't use slow HDD
--local-work-dir /mnt/slow_hdd/processing

# ✅ Use fast SSD/NVMe
--local-work-dir /tmp/stdf-processing  # tmpfs (RAM-backed)
# OR
--local-work-dir /data/nvme/stdf-processing  # Fast SSD
```

### 2. Network Mount Options

```bash
# Mount with caching for performance
sudo mount -t cifs //server/share/stdf /mnt/network/stdf \
    -o ro,cache=strict,username=user,password=pass

# Verify read-only
touch /mnt/network/stdf/test.txt
# Should fail: "Read-only file system" ✅
```

### 3. Monitor Disk Space (Local)

```bash
# Processing directory can fill up if errors occur
df -h /tmp/stdf-processing

# Cleanup old failed files periodically
find /tmp/stdf-processing/failed -type f -mtime +30 -delete
```

### 4. Database Maintenance

```sql
-- Cleanup old processing records (older than 6 months)
ALTER TABLE processed_files
DELETE WHERE processed_date < now() - INTERVAL 6 MONTH;

-- Optimize table
OPTIMIZE TABLE processed_files FINAL;
```

---

## 🚀 Quick Start Commands

```bash
# 1. Mount network folder (if needed)
sudo mount -t cifs //server/share/stdf /mnt/network/stdf -o ro,username=user

# 2. Verify structure
ls -la /mnt/network/stdf/
# Should see: OSBE25/ OSBE26/ OSBE27/ ...

# 3. Start watchdog
python watchdog_network_readonly.py \
    --network-path /mnt/network/stdf \
    --local-work-dir /tmp/stdf-processing \
    --clickhouse-host localhost \
    --clickhouse-port 9000

# 4. Monitor logs (in another terminal)
tail -f /tmp/stdf-processing/logs/stdf_ingestion_*.log

# 5. Check database
clickhouse-client --query "SELECT count(*) FROM processed_files"
```

---

## 📝 Summary

| Question | Answer |
|----------|--------|
| **Where to monitor?** | Main folder (parent of OSBE25), recursive |
| **Can modify network?** | NO - Read-only, no changes made |
| **Where to process?** | Local temp directory (copy → parse → cleanup) |
| **State tracking?** | Database only (processed_files table) |
| **Existing files?** | Processed on startup (initial scan) |
| **New files?** | Detected by watchdog (event-driven) |
| **Duplicates?** | Detected via hash (skip if already processed) |

---

**Use `watchdog_network_readonly.py` for your read-only network folder scenario!** ✅
