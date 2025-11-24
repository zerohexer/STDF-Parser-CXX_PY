# STDF Watchdog Ingestion System

Automated STDF file ingestion using filesystem monitoring with `watchdog`.

## Directory Structure

```
/data/stdf-ingestion/
├── incoming/                          # ← Watchdog monitors this directory
│   ├── {FACILITY}/                    # Level 1: Facility/Site (e.g., "OSBE25")
│   │   ├── {LOT}/                     # Level 2: Production Lot (e.g., "KEWGBCLD1U")
│   │   │   ├── {PRODUCT}/             # Level 3: Product/Device (e.g., "BE_HRG3301Y.06")
│   │   │   │   └── {TEST_PROGRAM}/    # Level 4: Test Program (e.g., "Prod_TPP202_03")
│   │   │   │       └── *.stdf
│   │
├── processing/                        # Files currently being parsed
│   └── {same structure as incoming}
│
├── processed/                         # Successfully ingested files
│   ├── {FACILITY}/
│   │   ├── {LOT}/
│   │   │   ├── {PRODUCT}/
│   │   │   │   ├── {TEST_PROGRAM}/
│   │   │   │       └── {YYYY}/        # Year-based archiving
│   │   │   │           └── {MM}/      # Month subdirectory
│   │   │   │               └── {DD}/  # Day subdirectory
│   │   │   │                   └── *.stdf
│
└── failed/                            # Parsing errors
    └── {same structure}
        └── *.error.log                # Error details for each failed file
```

## Hierarchy Rationale

| Level | Field | Example | Purpose |
|-------|-------|---------|---------|
| 1 | **FACILITY** | `OSBE25` | Testing site/location identifier |
| 2 | **LOT** | `KEWGBCLD1U` | Production lot/batch number |
| 3 | **PRODUCT** | `BE_HRG3301Y.06` | Device/product type under test |
| 4 | **TEST_PROGRAM** | `Prod_TPP202_03` | Test program name/version |

### Why This Order?

1. **FACILITY first**: Supports multi-site operations, allows per-facility routing
2. **LOT second**: Natural production grouping, time-bound batches
3. **PRODUCT third**: Same lot may contain multiple products
4. **TEST_PROGRAM fourth**: Same product may have multiple test programs (e.g., final test, burn-in, package test)

## Quick Start

### 1. Install Dependencies

```bash
pip install watchdog pandas clickhouse-driver
```

### 2. Setup Directory Structure

```bash
# Basic setup
python setup_ingestion_dirs.py

# Setup with example facilities
python setup_ingestion_dirs.py \
    --facilities OSBE25 OSBE26 \
    --lots LOT001 LOT002 \
    --products PRODUCT_A \
    --programs TEST_V1
```

### 3. Start Watchdog Service

```bash
# Local ClickHouse
python watchdog_ingestion.py

# Remote ClickHouse
python watchdog_ingestion.py \
    --clickhouse-host 192.168.1.100 \
    --clickhouse-port 9000

# Custom base path
python watchdog_ingestion.py \
    --base-path /mnt/data/stdf \
    --clickhouse-host localhost \
    --log-level DEBUG
```

### 4. Copy STDF Files to Incoming Directory

```bash
# Example: Copy file following the hierarchy
cp my_test_data.stdf \
    /data/stdf-ingestion/incoming/OSBE25/KEWGBCLD1U/BE_HRG3301Y.06/Prod_TPP202_03/
```

### 5. Monitor Logs

```bash
# Watch log file
tail -f stdf_ingestion.log

# Console output shows real-time processing
```

## Usage Examples

### Example 1: Single Facility, Multiple Lots

```
incoming/
└── OSBE25/
    ├── LOT001/
    │   └── PRODUCT_A/
    │       └── TEST_V1/
    │           ├── test1.stdf
    │           └── test2.stdf
    └── LOT002/
        └── PRODUCT_A/
            └── TEST_V1/
                └── test3.stdf
```

### Example 2: Multiple Facilities

```
incoming/
├── OSBE25/
│   └── LOT001/
│       └── PRODUCT_A/
│           └── TEST_V1/
│               └── file1.stdf
└── OSBE26/
    └── LOT001/
        └── PRODUCT_B/
            └── TEST_V2/
                └── file2.stdf
```

### Example 3: Same Product, Different Test Programs

```
incoming/
└── OSBE25/
    └── LOT001/
        └── HRG3301Y/
            ├── Final_Test/
            │   └── final.stdf
            ├── Burn_In/
            │   └── burnin.stdf
            └── Package_Test/
                └── package.stdf
```

## File Processing Flow

```
1. User copies file → incoming/{FACILITY}/{LOT}/{PRODUCT}/{PROGRAM}/file.stdf

2. Watchdog detects → Waits for file to stabilize (finish writing)

3. Move to processing → processing/{same path}/file.stdf

4. Parse STDF → Extract measurements using extract_all_measurements()

5. Push to ClickHouse → Insert into measurements, device_mapping, parameter_info, device_info

6. On Success → Move to processed/{same path}/{YYYY}/{MM}/{DD}/file.stdf

7. On Failure → Move to failed/{same path}/file.stdf + file.error.log
```

## Command-Line Options

```bash
python watchdog_ingestion.py --help

Options:
  --base-path PATH          Base directory for ingestion (default: /data/stdf-ingestion)
  --clickhouse-host HOST    ClickHouse host (default: localhost)
  --clickhouse-port PORT    ClickHouse port (default: 9000)
  --log-level LEVEL         Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
```

## Features

### Automatic File Stability Detection
- Waits for file size to stabilize before processing
- Avoids parsing incomplete files during network transfers
- 30-second timeout with 0.5s polling interval

### Duplicate Prevention
- Tracks files currently being processed
- Avoids processing the same file twice if triggered multiple times

### Error Handling
- Failed files moved to `failed/` directory
- Detailed error logs saved as `{filename}.error.log`
- Includes timestamp, error message, and full stack trace

### Date-Based Archiving
- Processed files organized by date: `YYYY/MM/DD/`
- Easy to find files processed on specific dates
- Supports long-term retention policies

### Recursive Monitoring
- Watches all subdirectories under `incoming/`
- Automatically creates missing parent directories
- Flexible hierarchy depth (can use fewer levels if needed)

## Integration with Existing Codebase

This watchdog system integrates with your existing STDF parser:

```python
# Uses your existing extraction function
from extract_all_measurements import extract_all_measurements

# Uses your existing ClickHouse push function
from clickhouse_utils import push_to_clickhouse
```

### Database Tables Populated

1. **measurements** - Core measurement data (MergeTree)
2. **device_mapping** - Device ID mapping
3. **parameter_info** - Test parameter mapping
4. **device_info** - Device context and metadata

All fields automatically extracted from STDF file headers:
- Facility, Lot, Product, Equipment, Operation
- Test Program name and version
- Device IDs, Bin codes
- Coordinates (X/Y pixel positions)
- Timestamps, measurement values

## Flexible Directory Structure

### Optional Levels

You **don't** have to use all 4 levels. Watchdog works with any depth:

```bash
# Minimal (just facility and lot)
incoming/OSBE25/LOT001/file.stdf

# Two levels (facility and product)
incoming/OSBE25/PRODUCT_A/file.stdf

# Full hierarchy
incoming/OSBE25/LOT001/PRODUCT_A/TEST_V1/file.stdf
```

Metadata extraction handles missing levels gracefully.

### Custom Naming

Directory names are **flexible**:
- Use your own naming conventions
- Spaces and special characters supported (enclose paths in quotes)
- Metadata from STDF headers takes precedence

## Running as a Service

### Systemd Service (Linux)

Create `/etc/systemd/system/stdf-ingestion.service`:

```ini
[Unit]
Description=STDF Watchdog Ingestion Service
After=network.target clickhouse-server.service

[Service]
Type=simple
User=stdf-user
WorkingDirectory=/home/user/STDF-Parser-CXX_PY
ExecStart=/usr/bin/python3 /home/user/STDF-Parser-CXX_PY/watchdog_ingestion.py \
    --base-path /data/stdf-ingestion \
    --clickhouse-host localhost \
    --clickhouse-port 9000 \
    --log-level INFO
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable stdf-ingestion
sudo systemctl start stdf-ingestion
sudo systemctl status stdf-ingestion
```

### Docker Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy STDF parser code
COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create ingestion directories
RUN python setup_ingestion_dirs.py --base-path /data/stdf-ingestion

# Run watchdog
CMD ["python", "watchdog_ingestion.py", \
     "--base-path", "/data/stdf-ingestion", \
     "--clickhouse-host", "clickhouse", \
     "--clickhouse-port", "9000"]
```

Run with volume mount:

```bash
docker run -d \
    --name stdf-ingestion \
    -v /data/stdf-ingestion:/data/stdf-ingestion \
    stdf-parser:latest
```

## Monitoring and Maintenance

### Check Processing Status

```bash
# Count files in each directory
find /data/stdf-ingestion/incoming -type f -name "*.stdf" | wc -l
find /data/stdf-ingestion/processing -type f -name "*.stdf" | wc -l
find /data/stdf-ingestion/processed -type f -name "*.stdf" | wc -l
find /data/stdf-ingestion/failed -type f -name "*.stdf" | wc -l
```

### Review Failed Files

```bash
# List all failed files
find /data/stdf-ingestion/failed -name "*.stdf"

# View error logs
cat /data/stdf-ingestion/failed/OSBE25/LOT001/PRODUCT_A/TEST_V1/file.error.log
```

### Cleanup Old Files

```bash
# Archive processed files older than 90 days
find /data/stdf-ingestion/processed -type f -name "*.stdf" -mtime +90 \
    -exec mv {} /data/stdf-ingestion/archive/ \;

# Delete failed files older than 180 days (after review)
find /data/stdf-ingestion/failed -type f -mtime +180 -delete
```

## Troubleshooting

### Files Not Being Processed

1. Check watchdog is running: `ps aux | grep watchdog_ingestion`
2. Check file permissions: `ls -la /data/stdf-ingestion/incoming/`
3. Check logs: `tail -f stdf_ingestion.log`
4. Verify file extension is `.stdf` (case-insensitive)

### ClickHouse Connection Errors

1. Verify ClickHouse is running: `clickhouse-client --query "SELECT 1"`
2. Check host/port: `netstat -tulpn | grep 9000`
3. Test connection: `clickhouse-client --host localhost --port 9000`

### Files Stuck in Processing

1. Check if parser crashed: Review logs for stack traces
2. Manual cleanup: Move file back to incoming or to failed
3. Restart watchdog service

### High Memory Usage

1. Processing very large STDF files: Increase system memory
2. Too many concurrent files: Add rate limiting (modify code)
3. Memory leak: Restart service periodically

## Advanced Configuration

### Parallel Processing (Future Enhancement)

Currently processes one file at a time. For parallel processing:

```python
# Modify STDFFileHandler to use ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor

class STDFFileHandler(FileSystemEventHandler):
    def __init__(self, config, clickhouse_host, clickhouse_port, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        # Submit processing jobs to thread pool
```

### Custom Validation Rules

Add validation before processing:

```python
def validate_file(file_path: Path, metadata: Dict) -> bool:
    """Custom validation logic"""
    # Example: Only process files from specific facilities
    if metadata['facility'] not in ['OSBE25', 'OSBE26']:
        return False
    # Example: Validate file size
    if file_path.stat().st_size < 1024:  # Less than 1KB
        return False
    return True
```

## Performance Metrics

Based on existing parser benchmarks:

- **Parsing Speed**: ~974,000 records/second
- **End-to-End Performance**: 7.7x faster than legacy pipeline
- **Database Insertion**: Bulk insert with connection pooling
- **File Handling**: Async monitoring, sequential processing

### Expected Throughput

| File Size | Records | Parse Time | Total Time (w/ DB) |
|-----------|---------|------------|-------------------|
| 10 MB | 100K | ~0.1s | ~0.5s |
| 100 MB | 1M | ~1s | ~3s |
| 1 GB | 10M | ~10s | ~25s |

*Times are approximate and depend on hardware/network*

## FAQ

**Q: Can I use a different directory hierarchy?**
A: Yes! The structure is flexible. Use any depth/naming that fits your workflow.

**Q: What happens if STDF file has different metadata than the directory path?**
A: STDF header metadata takes precedence. Directory structure is for organization only.

**Q: Can I manually move files between directories?**
A: Yes, but avoid moving files in `processing/` (active processing). Safe to move in `processed/` or `failed/`.

**Q: Does watchdog work with network drives/NFS?**
A: Yes, but file stability detection is critical. Increase timeout if needed.

**Q: Can I reprocess failed files?**
A: Yes! Move from `failed/` back to `incoming/` after fixing issues.

**Q: How do I add custom metadata extraction?**
A: Modify `_extract_metadata_from_path()` in `watchdog_ingestion.py` to parse filenames or add extra path levels.

## Support

For issues or questions:
- Check logs: `stdf_ingestion.log`
- Review error files in `failed/` directory
- Enable DEBUG logging for detailed output

## License

Same as STDF-Parser-CXX_PY project.
