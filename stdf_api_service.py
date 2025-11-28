#!/usr/bin/env python3
"""
STDF Ingestion API Service

FastAPI endpoint for processing STDF files via REST/SOAP requests.
Matches FactoryLook WCF service structure for MES integration.

Directory Structure:
    network_path/ProductClass/ProductType/Equipment/Operation/Lot/*.stdf

Example:
    PCBcast Pixlog 2217/KEWGBCLD1U/3CMT0101/5264/HRG3201Y.09/*.stdf

API Endpoint:
    POST /SetStdfFile
    {
        "LotNumber": "HRG3201Y.09",
        "OperationNumber": "5264",
        "OperationName": "CMOS Pre-Test (Room)",
        "EquipmentNumber": "3CMT0101",
        "ProductType": "KEWGBCLD1U",
        "ProductClass": "PCBcast Pixlog 2217"
    }

Usage:
    # Start API server
    python stdf_api_service.py --network-path //server/share/stdf --port 8000

    # Or with uvicorn
    uvicorn stdf_api_service:app --host 0.0.0.0 --port 8000
"""

import os
import sys
import hashlib
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import existing STDF processing modules
from extract_all_measurements import MeasurementExtractor
from clickhouse_utils import push_to_clickhouse

try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    ClickHouseClient = None


# =============================================================================
# Request/Response Models
# =============================================================================

class SetStdfFileRequest(BaseModel):
    """Request model matching FactoryLook SOAP structure"""
    LotNumber: str = Field(..., description="Lot number (e.g., HRG3201Y.09)")
    OperationNumber: str = Field(..., description="Operation number (e.g., 5264)")
    OperationName: str = Field(..., description="Operation name (e.g., CMOS Pre-Test)")
    EquipmentNumber: str = Field(..., description="Equipment number (e.g., 3CMT0101)")
    ProductType: str = Field(..., description="Product type (e.g., KEWGBCLD1U)")
    ProductClass: str = Field(..., description="Product class (e.g., PCBcast Pixlog 2217)")

    class Config:
        schema_extra = {
            "example": {
                "LotNumber": "HRG3201Y.09",
                "OperationNumber": "5264",
                "OperationName": "CMOS Pre-Test (Room)",
                "EquipmentNumber": "3CMT0101",
                "ProductType": "KEWGBCLD1U",
                "ProductClass": "PCBcast Pixlog 2217"
            }
        }


@dataclass
class FileProcessingResult:
    """Result of processing a single STDF file"""
    filename: str
    status: str  # 'success', 'skipped', 'failed'
    measurements: int = 0
    error: Optional[str] = None


class SetStdfFileResponse(BaseModel):
    """Response model for SetStdfFile endpoint"""
    status: str = Field(..., description="Overall status: success, partial, failed")
    lot: str = Field(..., description="Lot number processed")
    files_total: int = Field(..., description="Total STDF files found")
    files_processed: int = Field(..., description="Files successfully processed")
    files_skipped: int = Field(..., description="Files skipped (already processed)")
    files_failed: int = Field(..., description="Files that failed processing")
    total_measurements: int = Field(..., description="Total measurements inserted")
    processing_time_seconds: float = Field(..., description="Total processing time")
    details: List[Dict] = Field(..., description="Per-file processing details")
    message: str = Field(..., description="Human-readable message")


# =============================================================================
# File Hash Utilities
# =============================================================================

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for deduplication"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


# =============================================================================
# State Tracker (uses existing measurements table)
# =============================================================================

class STDFStateTracker:
    """Tracks processed files using existing measurements.file_hash field"""

    def __init__(self, clickhouse_host: str = "localhost", clickhouse_port: int = 9000,
                 clickhouse_database: str = "default", clickhouse_user: str = "default",
                 clickhouse_password: str = ""):
        self.logger = logging.getLogger(__name__)
        self.processed_hashes: Set[str] = set()
        self.client = None

        try:
            self.client = ClickHouseClient(
                host=clickhouse_host,
                port=clickhouse_port,
                database=clickhouse_database,
                user=clickhouse_user,
                password=clickhouse_password
            )
            self._load_processed_hashes()
            self.logger.info("State tracker initialized")
        except Exception as e:
            self.logger.warning(f"Could not connect to ClickHouse: {e}")
            self.logger.warning("File hash tracking disabled - will process all files")

    def _load_processed_hashes(self):
        """Load processed file hashes from measurements table"""
        if not self.client:
            return

        try:
            query = "SELECT DISTINCT file_hash FROM measurements WHERE file_hash != ''"
            result = self.client.execute(query)
            self.processed_hashes = {row[0] for row in result if row[0]}
            self.logger.info(f"Loaded {len(self.processed_hashes)} processed file hashes")
        except Exception as e:
            self.logger.warning(f"Could not load processed hashes: {e}")
            self.processed_hashes = set()

    def is_processed(self, file_hash: str) -> bool:
        """Check if file has been processed"""
        return file_hash in self.processed_hashes

    def mark_completed(self, file_hash: str):
        """Add file hash to processed set (already in measurements table)"""
        self.processed_hashes.add(file_hash)


# =============================================================================
# Core STDF Processor
# =============================================================================

class STDFLotProcessor:
    """Core processor for STDF lot processing"""

    def __init__(self, network_path: str, local_work_dir: str,
                 clickhouse_host: str, clickhouse_port: int,
                 clickhouse_database: str = "default",
                 clickhouse_user: str = "default",
                 clickhouse_password: str = ""):
        self.network_path = Path(network_path)
        self.local_work_dir = Path(local_work_dir)
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_database = clickhouse_database
        self.clickhouse_user = clickhouse_user
        self.clickhouse_password = clickhouse_password
        self.logger = logging.getLogger(__name__)

        # Create local working directory
        self.local_work_dir.mkdir(parents=True, exist_ok=True)

        # Initialize state tracker
        self.state_tracker = STDFStateTracker(
            clickhouse_host, clickhouse_port,
            clickhouse_database, clickhouse_user, clickhouse_password
        )

    def build_lot_path(self, product_class: str, product_type: str,
                       equipment: str, operation: str, lot: str) -> Path:
        """
        Build path to lot directory

        Structure: ProductClass/ProductType/Equipment/Operation/Lot
        Example: PCBcast Pixlog 2217/KEWGBCLD1U/3CMT0101/5264/HRG3201Y.09
        """
        return self.network_path / product_class / product_type / equipment / operation / lot

    def process_lot(self, request: SetStdfFileRequest) -> SetStdfFileResponse:
        """
        Process all STDF files for a specific lot

        Args:
            request: SetStdfFileRequest with lot parameters

        Returns:
            SetStdfFileResponse with processing results
        """
        start_time = datetime.now()

        self.logger.info("=" * 70)
        self.logger.info(f"Processing lot: {request.LotNumber}")
        self.logger.info(f"  Product Class: {request.ProductClass}")
        self.logger.info(f"  Product Type:  {request.ProductType}")
        self.logger.info(f"  Equipment:     {request.EquipmentNumber}")
        self.logger.info(f"  Operation:     {request.OperationNumber} ({request.OperationName})")

        # Build path to lot directory
        lot_path = self.build_lot_path(
            request.ProductClass,
            request.ProductType,
            request.EquipmentNumber,
            request.OperationNumber,
            request.LotNumber
        )

        self.logger.info(f"  Lot Path:      {lot_path}")

        # Check if lot directory exists
        if not lot_path.exists():
            error_msg = f"Lot directory not found: {lot_path}"
            self.logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Find all STDF files in lot directory
        stdf_files = list(lot_path.glob("*.stdf"))
        self.logger.info(f"  Found {len(stdf_files)} STDF files")

        if not stdf_files:
            return SetStdfFileResponse(
                status="success",
                lot=request.LotNumber,
                files_total=0,
                files_processed=0,
                files_skipped=0,
                files_failed=0,
                total_measurements=0,
                processing_time_seconds=0,
                details=[],
                message="No STDF files found in lot directory"
            )

        # Process each file
        results = []
        for file_path in stdf_files:
            result = self._process_single_file(file_path)
            results.append(result)
            self.logger.info(f"    {result.filename}: {result.status} "
                           f"({result.measurements} measurements)")

        # Calculate summary
        files_processed = sum(1 for r in results if r.status == 'success')
        files_skipped = sum(1 for r in results if r.status == 'skipped')
        files_failed = sum(1 for r in results if r.status == 'failed')
        total_measurements = sum(r.measurements for r in results)

        processing_time = (datetime.now() - start_time).total_seconds()

        # Determine overall status
        if files_failed == 0:
            status = "success"
        elif files_processed > 0:
            status = "partial"
        else:
            status = "failed"

        # Build response
        response = SetStdfFileResponse(
            status=status,
            lot=request.LotNumber,
            files_total=len(stdf_files),
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_failed=files_failed,
            total_measurements=total_measurements,
            processing_time_seconds=round(processing_time, 2),
            details=[{
                "filename": r.filename,
                "status": r.status,
                "measurements": r.measurements,
                "error": r.error
            } for r in results],
            message=f"Processed {files_processed}/{len(stdf_files)} files successfully"
        )

        self.logger.info(f"  Status: {status}")
        self.logger.info(f"  Processed: {files_processed}, Skipped: {files_skipped}, Failed: {files_failed}")
        self.logger.info(f"  Total measurements: {total_measurements}")
        self.logger.info(f"  Processing time: {processing_time:.2f}s")
        self.logger.info("=" * 70)

        return response

    def _process_single_file(self, file_path: Path) -> FileProcessingResult:
        """
        Process a single STDF file

        Args:
            file_path: Path to STDF file

        Returns:
            FileProcessingResult
        """
        local_file = None

        try:
            # Calculate file hash
            file_hash = calculate_file_hash(str(file_path))

            # Check if already processed
            if self.state_tracker.is_processed(file_hash):
                return FileProcessingResult(
                    filename=file_path.name,
                    status='skipped',
                    measurements=0
                )

            # Copy to local for processing
            local_file = self.local_work_dir / f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{file_path.suffix}"
            import shutil
            shutil.copy2(str(file_path), str(local_file))

            # Parse STDF file
            extractor = MeasurementExtractor()
            measurements = extractor.extract_measurements(str(local_file))

            if not measurements:
                raise ValueError("No measurements extracted from STDF file")

            measurement_count = len(measurements)

            # Push to ClickHouse
            push_to_clickhouse(
                extractor,
                host=self.clickhouse_host,
                port=self.clickhouse_port,
                database=self.clickhouse_database,
                user=self.clickhouse_user,
                password=self.clickhouse_password
            )

            # Mark as completed
            self.state_tracker.mark_completed(file_hash)

            # Cleanup local copy
            if local_file and local_file.exists():
                local_file.unlink()

            return FileProcessingResult(
                filename=file_path.name,
                status='success',
                measurements=measurement_count
            )

        except Exception as e:
            self.logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)

            # Cleanup local copy
            if local_file and local_file.exists():
                try:
                    local_file.unlink()
                except:
                    pass

            return FileProcessingResult(
                filename=file_path.name,
                status='failed',
                measurements=0,
                error=str(e)
            )


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="STDF Ingestion API",
    description="Process STDF files for semiconductor test data ingestion",
    version="1.0.0"
)

# Global processor instance (initialized in main())
processor: Optional[STDFLotProcessor] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "STDF Ingestion API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "network_path": str(processor.network_path) if processor else None,
        "clickhouse_host": processor.clickhouse_host if processor else None,
        "processed_files": len(processor.state_tracker.processed_hashes) if processor else 0
    }


@app.post("/SetStdfFile", response_model=SetStdfFileResponse)
async def set_stdf_file(request: SetStdfFileRequest, background_tasks: BackgroundTasks):
    """
    Process STDF files for a specific lot (main endpoint for MES integration)

    This endpoint matches the FactoryLook WCF service structure.
    Called after CMOS Move Out (MVOU) to process test data.

    Args:
        request: SetStdfFileRequest with lot parameters

    Returns:
        SetStdfFileResponse with processing results
    """
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")

    try:
        result = processor.process_lot(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/SetStdfFile.svc", response_model=SetStdfFileResponse)
async def set_stdf_file_soap(request: SetStdfFileRequest):
    """
    SOAP-compatible endpoint for WCF clients

    Same functionality as /SetStdfFile but with .svc extension for compatibility
    """
    return await set_stdf_file(request, BackgroundTasks())


# =============================================================================
# Main Entry Point
# =============================================================================

def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stdf_api_service.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='STDF Ingestion API Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start API server
  python stdf_api_service.py --network-path //server/share/stdf --port 8000

  # With custom ClickHouse (with credentials)
  python stdf_api_service.py \\
      --network-path /mnt/network/stdf \\
      --ch-host 10.96.38.217 \\
      --ch-port 9000 \\
      --ch-database iswc \\
      --ch-user admin \\
      --ch-password secret_pass123 \\
      --port 8000

  # Test with curl
  curl -X POST http://localhost:8000/SetStdfFile \\
    -H "Content-Type: application/json" \\
    -d '{
      "LotNumber": "HRG3201Y.09",
      "OperationNumber": "5264",
      "OperationName": "CMOS Pre-Test (Room)",
      "EquipmentNumber": "3CMT0101",
      "ProductType": "KEWGBCLD1U",
      "ProductClass": "PCBcast Pixlog 2217"
    }'
        """
    )

    parser.add_argument('--network-path', required=True,
                       help='Network folder path (e.g., //server/share/stdf)')
    parser.add_argument('--local-work-dir', default='/tmp/stdf-api',
                       help='Local working directory (default: /tmp/stdf-api)')
    parser.add_argument('--clickhouse-host', '--ch-host', default='localhost',
                       help='ClickHouse host (default: localhost)')
    parser.add_argument('--clickhouse-port', '--ch-port', type=int, default=9000,
                       help='ClickHouse port (default: 9000)')
    parser.add_argument('--clickhouse-database', '--ch-database', default='default',
                       help='ClickHouse database (default: default)')
    parser.add_argument('--clickhouse-user', '--ch-user', default='default',
                       help='ClickHouse user (default: default)')
    parser.add_argument('--clickhouse-password', '--ch-password', default='',
                       help='ClickHouse password (default: empty)')
    parser.add_argument('--port', type=int, default=8000,
                       help='API server port (default: 8000)')
    parser.add_argument('--host', default='0.0.0.0',
                       help='API server host (default: 0.0.0.0)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("STDF Ingestion API Service")
    logger.info("=" * 70)
    logger.info(f"Network Path:    {args.network_path}")
    logger.info(f"Local Work Dir:  {args.local_work_dir}")
    logger.info(f"ClickHouse:      {args.clickhouse_host}:{args.clickhouse_port}")
    logger.info(f"  Database:      {args.clickhouse_database}")
    logger.info(f"  User:          {args.clickhouse_user}")
    logger.info(f"API Endpoint:    http://{args.host}:{args.port}")
    logger.info("=" * 70)

    # Verify network path exists
    if not Path(args.network_path).exists():
        logger.error(f"Network path does not exist: {args.network_path}")
        sys.exit(1)

    # Initialize global processor
    global processor
    processor = STDFLotProcessor(
        network_path=args.network_path,
        local_work_dir=args.local_work_dir,
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port,
        clickhouse_database=args.clickhouse_database,
        clickhouse_user=args.clickhouse_user,
        clickhouse_password=args.clickhouse_password
    )

    # Start API server
    logger.info("Starting API server...")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
