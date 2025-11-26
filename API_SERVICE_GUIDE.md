# STDF API Service Guide

**API-First Architecture for MES Integration**

Provides REST/SOAP endpoints for processing STDF files on-demand.
Designed for FactoryLook MES integration after CMOS Move Out (MVOU).

---

## 📁 Directory Structure

```
network_path/
└── ProductClass/              ← From osr:ProductClass
    └── ProductType/           ← From osr:ProductType
        └── EquipmentNumber/   ← From osr:EquipmentNumber
            └── OperationNumber/ ← From osr:OperationNumber
                └── LotNumber/   ← From osr:LotNumber
                    └── *.stdf
```

**Example:**
```
//server/share/stdf/
└── PCBcast Pixlog 2217/
    └── KEWGBCLD1U/
        └── 3CMT0101/
            └── 5264/
                └── HRG3201Y.09/
                    ├── file1.stdf
                    ├── file2.stdf
                    └── file3.stdf
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start API Server

```bash
# Basic usage
python stdf_api_service.py --network-path //server/share/stdf

# With custom ClickHouse
python stdf_api_service.py \
    --network-path /mnt/network/stdf \
    --clickhouse-host 192.168.1.100 \
    --clickhouse-port 9000 \
    --port 8000
```

**Server starts at:** `http://0.0.0.0:8000`

### 3. Test with Emulator (No MES needed!)

```bash
python emulate_mes_call.py \
    --lot HRG3201Y.09 \
    --operation 5264 \
    --operation-name "CMOS Pre-Test (Room)" \
    --equipment 3CMT0101 \
    --product-type KEWGBCLD1U \
    --product-class "PCBcast Pixlog 2217"
```

---

## 🔌 API Endpoints

### **POST /SetStdfFile**

Main endpoint for MES integration (matches FactoryLook SOAP structure).

**Request:**
```json
{
  "LotNumber": "HRG3201Y.09",
  "OperationNumber": "5264",
  "OperationName": "CMOS Pre-Test (Room)",
  "EquipmentNumber": "3CMT0101",
  "ProductType": "KEWGBCLD1U",
  "ProductClass": "PCBcast Pixlog 2217"
}
```

**Response:**
```json
{
  "status": "success",
  "lot": "HRG3201Y.09",
  "files_total": 3,
  "files_processed": 2,
  "files_skipped": 1,
  "files_failed": 0,
  "total_measurements": 125432,
  "processing_time_seconds": 2.45,
  "details": [
    {
      "filename": "file1.stdf",
      "status": "success",
      "measurements": 62500,
      "error": null
    },
    {
      "filename": "file2.stdf",
      "status": "skipped",
      "measurements": 0,
      "error": null
    },
    {
      "filename": "file3.stdf",
      "status": "success",
      "measurements": 62932,
      "error": null
    }
  ],
  "message": "Processed 2/3 files successfully"
}
```

**Status Codes:**
- `200 OK` - Processing complete (check `status` field)
- `404 Not Found` - Lot directory doesn't exist
- `500 Internal Server Error` - Processing error

**Status Values:**
- `"success"` - All files processed successfully
- `"partial"` - Some files failed
- `"failed"` - All files failed

---

### **POST /SetStdfFile.svc**

SOAP-compatible endpoint for WCF clients (same functionality).

---

### **GET /**

Health check endpoint.

**Response:**
```json
{
  "service": "STDF Ingestion API",
  "status": "running",
  "version": "1.0.0"
}
```

---

### **GET /health**

Detailed health check.

**Response:**
```json
{
  "status": "healthy",
  "network_path": "//server/share/stdf",
  "clickhouse_host": "localhost",
  "processed_files": 15234
}
```

---

## 💻 Usage Examples

### Using curl

```bash
# Basic request
curl -X POST http://localhost:8000/SetStdfFile \
  -H "Content-Type: application/json" \
  -d '{
    "LotNumber": "HRG3201Y.09",
    "OperationNumber": "5264",
    "OperationName": "CMOS Pre-Test (Room)",
    "EquipmentNumber": "3CMT0101",
    "ProductType": "KEWGBCLD1U",
    "ProductClass": "PCBcast Pixlog 2217"
  }'

# Save response to file
curl -X POST http://localhost:8000/SetStdfFile \
  -H "Content-Type: application/json" \
  -d @request.json \
  -o response.json

# Check health
curl http://localhost:8000/health
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/SetStdfFile",
    json={
        "LotNumber": "HRG3201Y.09",
        "OperationNumber": "5264",
        "OperationName": "CMOS Pre-Test (Room)",
        "EquipmentNumber": "3CMT0101",
        "ProductType": "KEWGBCLD1U",
        "ProductClass": "PCBcast Pixlog 2217"
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Files processed: {result['files_processed']}")
print(f"Measurements: {result['total_measurements']}")
```

### Using MES Emulator

```bash
# From SOAP message values
python emulate_mes_call.py \
    --lot HRG3201Y.09 \
    --operation 5264 \
    --operation-name "CMOS Pre-Test (Room)" \
    --equipment 3CMT0101 \
    --product-type KEWGBCLD1U \
    --product-class "PCBcast Pixlog 2217"

# Custom API URL
python emulate_mes_call.py \
    --api-url http://192.168.1.100:8000/SetStdfFile \
    --lot HRG3201Y.09 \
    --operation 5264 \
    --equipment 3CMT0101 \
    --product-type KEWGBCLD1U \
    --product-class "PCBcast Pixlog 2217"
```

---

## 🔄 Processing Flow

```
1. MES (FactoryLook) completes CMOS Move Out (MVOU)
   └─ STDF files ready in network folder
      └─ PCBcast Pixlog 2217/KEWGBCLD1U/3CMT0101/5264/HRG3201Y.09/*.stdf

2. MES calls SetStdfFile API
   └─ POST /SetStdfFile
   └─ Request: { "LotNumber": "HRG3201Y.09", ... }

3. API receives request
   └─ Build path from parameters
   └─ Find all *.stdf files in lot folder

4. For each STDF file:
   └─ Calculate file_hash (SHA256)
   └─ Check if already processed (query measurements table)
   ├─ Already processed? → Skip ✅
   └─ New file? → Process ⬇️
      └─ Copy to local temp directory
      └─ Parse STDF (extract_all_measurements)
      └─ Push to ClickHouse (4 tables)
      └─ Cleanup local copy

5. Return response to MES
   └─ Status: success/partial/failed
   └─ File counts, measurement counts, processing time
   └─ Per-file details
```

---

## 🗄️ State Tracking

**Uses existing measurements.file_hash field** (no new tables!)

```sql
-- Check if file already processed
SELECT DISTINCT file_hash FROM measurements WHERE file_hash != ''

-- File hash included automatically when push_to_clickhouse() is called
```

**Deduplication:**
- Calculate SHA256 hash of file content
- Query measurements table for hash
- If found → Skip (already processed)
- If not found → Process normally

**Benefits:**
- ✅ No schema changes needed
- ✅ Automatic retry for failed files (hash not in DB)
- ✅ Works across different facilities/lots (same file = skip)

---

## 📊 Database Tables Populated

All standard tables (existing infrastructure):

1. **measurements** - Core measurement data
2. **device_mapping** - Device ID mapping
3. **parameter_info** - Test parameter mapping
4. **device_info** - Device context and metadata

---

## 🎛️ Configuration Options

```bash
python stdf_api_service.py --help
```

| Option | Default | Description |
|--------|---------|-------------|
| `--network-path` | *Required* | Network folder path |
| `--local-work-dir` | `/tmp/stdf-api` | Local temp directory |
| `--clickhouse-host` | `localhost` | ClickHouse host |
| `--clickhouse-port` | `9000` | ClickHouse port |
| `--port` | `8000` | API server port |
| `--host` | `0.0.0.0` | API server host |
| `--log-level` | `INFO` | Logging level |

---

## 🔍 Monitoring

### Check API Status

```bash
# Health check
curl http://localhost:8000/health

# Get processed file count
curl http://localhost:8000/health | jq '.processed_files'
```

### View Logs

```bash
# Real-time logs
tail -f stdf_api_service.log

# Search for errors
grep ERROR stdf_api_service.log

# Count successful lots
grep "Status: success" stdf_api_service.log | wc -l
```

### Query Database

```sql
-- Total processed files
SELECT COUNT(DISTINCT file_hash) FROM measurements WHERE file_hash != '';

-- Recent processing activity
SELECT
    wfi_facility,
    wl_lot_name,
    COUNT(*) as measurements,
    MAX(wptm_created_date) as last_processed
FROM measurements
WHERE wptm_created_date > now() - INTERVAL 1 DAY
GROUP BY wfi_facility, wl_lot_name
ORDER BY last_processed DESC;

-- Files by product class (from device_info)
SELECT
    wfi_facility,
    COUNT(DISTINCT wld_id) as devices,
    COUNT(*) as measurements
FROM device_info
GROUP BY wfi_facility
ORDER BY measurements DESC;
```

---

## 🚨 Error Handling

### Lot Directory Not Found

**Response:** `404 Not Found`
```json
{
  "detail": "Lot directory not found: //server/share/.../HRG3201Y.09"
}
```

**Solution:** Verify directory structure and parameters match.

### No STDF Files Found

**Response:** `200 OK`
```json
{
  "status": "success",
  "files_total": 0,
  "message": "No STDF files found in lot directory"
}
```

### Partial Success (Some Files Failed)

**Response:** `200 OK`
```json
{
  "status": "partial",
  "files_processed": 2,
  "files_failed": 1,
  "details": [
    {"filename": "file1.stdf", "status": "success"},
    {"filename": "file2.stdf", "status": "success"},
    {"filename": "file3.stdf", "status": "failed", "error": "Corrupted file"}
  ]
}
```

### All Files Failed

**Response:** `200 OK`
```json
{
  "status": "failed",
  "files_processed": 0,
  "files_failed": 3
}
```

---

## 🔧 Deployment

### Development

```bash
# Run directly
python stdf_api_service.py --network-path ./STDF_Files --port 8000
```

### Production (systemd)

Create `/etc/systemd/system/stdf-api.service`:

```ini
[Unit]
Description=STDF Ingestion API Service
After=network.target clickhouse-server.service

[Service]
Type=simple
User=stdf-user
WorkingDirectory=/opt/stdf-parser
ExecStart=/usr/bin/python3 /opt/stdf-parser/stdf_api_service.py \
    --network-path //server/share/stdf \
    --clickhouse-host localhost \
    --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable stdf-api
sudo systemctl start stdf-api
sudo systemctl status stdf-api
```

### Production (Docker)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["python", "stdf_api_service.py", \
     "--network-path", "/data/stdf", \
     "--clickhouse-host", "clickhouse", \
     "--port", "8000"]
```

Run:
```bash
docker run -d \
    --name stdf-api \
    -p 8000:8000 \
    -v /mnt/network/stdf:/data/stdf:ro \
    stdf-parser:latest
```

---

## 🔗 MES Integration

### FactoryLook Configuration

**Endpoint:** `http://your-server:8000/SetStdfFile`

**Request Format:** JSON (REST) or SOAP

**When to Call:** After CMOS Move Out (MVOU) completion

**Parameters from MES:**
- Extract from STDF file metadata
- Or from MES database
- Match to directory structure

### Network Configuration

**Firewall Rules:**
```bash
# Allow inbound connections to API
sudo ufw allow 8000/tcp

# Or specific source (MES server)
sudo ufw allow from 192.168.1.50 to any port 8000
```

**Load Balancing** (optional):
```
nginx → API Server 1 (port 8000)
     → API Server 2 (port 8001)
     → API Server 3 (port 8002)
```

---

## ⚡ Performance

**Expected Throughput:**
- Single file (100 MB, 1M records): ~1-2 seconds
- Typical lot (10 files, 10M records): ~10-20 seconds
- Large lot (50 files, 50M records): ~60-120 seconds

**Optimization:**
- Use local SSD for temp directory (`--local-work-dir`)
- ClickHouse on same network (low latency)
- Multiple API instances for parallel lots

---

## ❓ FAQ

**Q: Can I process the same lot twice?**
A: Yes! Files already processed are automatically skipped (file_hash check).

**Q: What if some files fail?**
A: Response shows `"status": "partial"` with per-file details. Failed files will retry on next call.

**Q: Can I call the API manually for testing?**
A: Yes! Use `emulate_mes_call.py` or curl.

**Q: Does it work without MES?**
A: Yes! Use the emulator or curl to trigger processing manually.

**Q: Can I auto-process without MES?**
A: Yes! Use cron/scheduler to call API periodically, or add watchdog wrapper (10 lines of code).

**Q: How do I know if processing succeeded?**
A: Check response `status` field and `files_processed` count.

**Q: Where are logs stored?**
A: `stdf_api_service.log` in working directory.

---

## 📝 Summary

| Aspect | Implementation |
|--------|----------------|
| **Endpoint** | POST /SetStdfFile |
| **Trigger** | MES calls after MVOU |
| **Directory** | ProductClass/ProductType/Equipment/Operation/Lot |
| **Deduplication** | file_hash in measurements table |
| **Response** | JSON with status, counts, details |
| **Emulator** | `emulate_mes_call.py` for testing |
| **MES-Ready** | ✅ Yes (matches SOAP structure) |

---

**Start the API service and use the emulator to test without MES!** 🚀

```bash
# Terminal 1: Start API
python stdf_api_service.py --network-path ./STDF_Files

# Terminal 2: Test with emulator
python emulate_mes_call.py \
    --lot HRG3201Y.09 \
    --operation 5264 \
    --equipment 3CMT0101 \
    --product-type KEWGBCLD1U \
    --product-class "PCBcast Pixlog 2217"
```
