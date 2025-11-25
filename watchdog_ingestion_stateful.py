#!/usr/bin/env python3
"""
STDF Watchdog Ingestion with State Management

Features:
- Monitors top-level directory recursively (detects all OSBE25, OSBE26, etc.)
- Tracks processed files via file_hash in ClickHouse (prevents duplicates)
- File movement workflow: incoming → processing → processed/failed
- Supports dynamic facility/lot/product/program folder structure

Directory Structure:
    incoming/{FACILITY}/{LOT}/{PRODUCT}/{TEST_PROGRAM}/*.stdf

Example:
    incoming/OSBE25/KEWGBCLD1U/HRG3301Y.06/Prod_TPP202_03/file.stdf
"""

import os
import sys
import time
import shutil
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import existing STDF processing modules
from extract_all_measurements import extract_all_measurements
from clickhouse_utils import push_to_clickhouse

# ClickHouse client for state tracking
try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    ClickHouseClient = None


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for deduplication"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class ProcessingStateTracker:
    """Tracks processed files to prevent duplicates"""

    def __init__(self, clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000,
                 use_database: bool = True):
        self.use_database = use_database and (ClickHouseClient is not None)
        self.logger = logging.getLogger(__name__)

        # In-memory cache for fast lookups
        self.processed_hashes: Set[str] = set()

        if self.use_database:
            try:
                self.client = ClickHouseClient(host=clickhouse_host, port=clickhouse_port)
                self._ensure_tracking_table()
                self._load_processed_hashes()
            except Exception as e:
                self.logger.warning(f"Could not connect to ClickHouse for state tracking: {e}")
                self.logger.warning("Falling back to file-movement-only state management")
                self.use_database = False

    def _ensure_tracking_table(self):
        """Create processed_files tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS processed_files (
            file_hash String,
            file_name String,
            file_path String,
            facility String,
            lot String,
            product String,
            test_program String,
            file_size_bytes UInt64,
            processed_date DateTime,
            status String,  -- 'processing', 'completed', 'failed'
            error_message String
        ) ENGINE = MergeTree()
        ORDER BY (facility, processed_date)
        """
        self.client.execute(create_table_sql)
        self.logger.info("Ensured processed_files tracking table exists")

    def _load_processed_hashes(self):
        """Load all processed file hashes into memory cache"""
        query = "SELECT file_hash FROM processed_files WHERE status = 'completed'"
        result = self.client.execute(query)
        self.processed_hashes = {row[0] for row in result}
        self.logger.info(f"Loaded {len(self.processed_hashes)} processed file hashes into cache")

    def is_processed(self, file_hash: str) -> bool:
        """Check if file hash has been processed"""
        return file_hash in self.processed_hashes

    def mark_processing(self, file_hash: str, file_path: Path, metadata: Dict):
        """Mark file as currently being processed"""
        if not self.use_database:
            return

        insert_sql = """
        INSERT INTO processed_files
        (file_hash, file_name, file_path, facility, lot, product, test_program,
         file_size_bytes, processed_date, status, error_message)
        VALUES
        """

        try:
            file_size = file_path.stat().st_size
            self.client.execute(insert_sql, [{
                'file_hash': file_hash,
                'file_name': file_path.name,
                'file_path': str(file_path),
                'facility': metadata.get('facility', 'UNKNOWN'),
                'lot': metadata.get('lot', 'UNKNOWN'),
                'product': metadata.get('product', 'UNKNOWN'),
                'test_program': metadata.get('test_program', 'UNKNOWN'),
                'file_size_bytes': file_size,
                'processed_date': datetime.now(),
                'status': 'processing',
                'error_message': ''
            }])
        except Exception as e:
            self.logger.error(f"Failed to mark file as processing: {e}")

    def mark_completed(self, file_hash: str):
        """Mark file as successfully processed"""
        if not self.use_database:
            return

        update_sql = """
        ALTER TABLE processed_files
        UPDATE status = 'completed'
        WHERE file_hash = %(file_hash)s
        """

        try:
            self.client.execute(update_sql, {'file_hash': file_hash})
            self.processed_hashes.add(file_hash)
        except Exception as e:
            self.logger.error(f"Failed to mark file as completed: {e}")

    def mark_failed(self, file_hash: str, error_message: str):
        """Mark file as failed processing"""
        if not self.use_database:
            return

        update_sql = """
        ALTER TABLE processed_files
        UPDATE status = 'failed', error_message = %(error_message)s
        WHERE file_hash = %(file_hash)s
        """

        try:
            self.client.execute(update_sql, {
                'file_hash': file_hash,
                'error_message': error_message[:1000]  # Limit length
            })
        except Exception as e:
            self.logger.error(f"Failed to mark file as failed: {e}")


class STDFIngestionConfig:
    """Configuration for STDF ingestion with 4-level hierarchy"""

    def __init__(self, base_path: str = "/data/stdf-ingestion"):
        self.base_path = Path(base_path)
        self.incoming = self.base_path / "incoming"
        self.processing = self.base_path / "processing"
        self.processed = self.base_path / "processed"
        self.failed = self.base_path / "failed"
        self.duplicates = self.base_path / "duplicates"  # For already-processed files

        # Create directories
        for path in [self.incoming, self.processing, self.processed, self.failed, self.duplicates]:
            path.mkdir(parents=True, exist_ok=True)

    def get_relative_path(self, file_path: Path) -> Path:
        """Get relative path from incoming directory"""
        try:
            return file_path.relative_to(self.incoming)
        except ValueError:
            return Path(file_path.name)

    def extract_metadata_from_path(self, file_path: Path) -> Dict[str, str]:
        """
        Extract metadata from directory structure

        Expected: incoming/FACILITY/LOT/PRODUCT/TEST_PROGRAM/file.stdf
        """
        rel_path = self.get_relative_path(file_path)
        parts = rel_path.parts

        metadata = {
            'facility': parts[0] if len(parts) > 1 else 'UNKNOWN',
            'lot': parts[1] if len(parts) > 2 else 'UNKNOWN',
            'product': parts[2] if len(parts) > 3 else 'UNKNOWN',
            'test_program': parts[3] if len(parts) > 4 else 'UNKNOWN',
        }

        return metadata

    def get_processing_path(self, file_path: Path) -> Path:
        """Get processing directory path"""
        rel_path = self.get_relative_path(file_path)
        return self.processing / rel_path

    def get_processed_path(self, file_path: Path) -> Path:
        """Get processed directory path with date partitioning"""
        rel_path = self.get_relative_path(file_path)
        now = datetime.now()
        date_path = Path(str(now.year)) / f"{now.month:02d}" / f"{now.day:02d}"
        return self.processed / rel_path.parent / date_path / rel_path.name

    def get_failed_path(self, file_path: Path) -> Path:
        """Get failed directory path"""
        rel_path = self.get_relative_path(file_path)
        return self.failed / rel_path

    def get_duplicate_path(self, file_path: Path) -> Path:
        """Get duplicate directory path"""
        rel_path = self.get_relative_path(file_path)
        return self.duplicates / rel_path


class STDFFileHandler(FileSystemEventHandler):
    """Handles STDF file events with state tracking"""

    def __init__(self, config: STDFIngestionConfig,
                 state_tracker: ProcessingStateTracker,
                 clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000):
        self.config = config
        self.state_tracker = state_tracker
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.logger = logging.getLogger(__name__)
        self.processing_files = set()  # Prevent concurrent processing

    def on_created(self, event):
        """Called when file is created"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .stdf files
        if file_path.suffix.lower() != '.stdf':
            return

        # Wait for file stability
        self._wait_for_file_stable(file_path)

        # Process the file
        self.process_stdf_file(file_path)

    def _wait_for_file_stable(self, file_path: Path, timeout: int = 30):
        """Wait for file size to stabilize (file finished writing)"""
        if not file_path.exists():
            return

        last_size = -1
        stable_count = 0
        start_time = time.time()

        while stable_count < 3:
            if time.time() - start_time > timeout:
                self.logger.warning(f"Timeout waiting for file stability: {file_path}")
                break

            try:
                current_size = file_path.stat().st_size
                if current_size == last_size:
                    stable_count += 1
                else:
                    stable_count = 0
                last_size = current_size
                time.sleep(0.5)
            except (OSError, FileNotFoundError):
                break

    def process_stdf_file(self, file_path: Path):
        """Process STDF file with duplicate detection"""

        # Prevent concurrent processing of same file
        if str(file_path) in self.processing_files:
            self.logger.info(f"File already being processed: {file_path}")
            return

        self.processing_files.add(str(file_path))

        try:
            self.logger.info(f"Starting ingestion: {file_path}")

            # Step 1: Extract metadata from directory structure
            metadata = self.config.extract_metadata_from_path(file_path)
            self.logger.info(f"Metadata: Facility={metadata['facility']}, "
                           f"Lot={metadata['lot']}, Product={metadata['product']}, "
                           f"Program={metadata['test_program']}")

            # Step 2: Calculate file hash for deduplication
            file_hash = calculate_file_hash(str(file_path))
            self.logger.debug(f"File hash: {file_hash}")

            # Step 3: Check if already processed
            if self.state_tracker.is_processed(file_hash):
                self.logger.warning(f"DUPLICATE DETECTED: File already processed (hash: {file_hash})")

                # Move to duplicates folder
                duplicate_path = self.config.get_duplicate_path(file_path)
                duplicate_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(duplicate_path))
                self.logger.info(f"Moved duplicate to: {duplicate_path}")
                return

            # Step 4: Mark as processing in database
            self.state_tracker.mark_processing(file_hash, file_path, metadata)

            # Step 5: Move to processing directory
            processing_path = self.config.get_processing_path(file_path)
            processing_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(processing_path))
            self.logger.info(f"Moved to processing: {processing_path}")

            # Step 6: Parse STDF file
            self.logger.info(f"Parsing STDF file...")
            measurements_df = extract_all_measurements(str(processing_path))

            if measurements_df.empty:
                raise ValueError("No measurements extracted from STDF file")

            self.logger.info(f"Extracted {len(measurements_df)} measurements")

            # Step 7: Push to ClickHouse
            self.logger.info(f"Pushing to ClickHouse: {self.clickhouse_host}:{self.clickhouse_port}")
            push_to_clickhouse(
                measurements_df,
                host=self.clickhouse_host,
                port=self.clickhouse_port
            )
            self.logger.info(f"Successfully pushed {len(measurements_df)} records")

            # Step 8: Mark as completed in database
            self.state_tracker.mark_completed(file_hash)

            # Step 9: Move to processed directory
            processed_path = self.config.get_processed_path(processing_path)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(processing_path), str(processed_path))
            self.logger.info(f"Moved to processed: {processed_path}")

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)

            # Mark as failed in database
            try:
                file_hash = calculate_file_hash(str(file_path))
                self.state_tracker.mark_failed(file_hash, str(e))
            except:
                pass

            # Move to failed directory
            try:
                failed_path = self.config.get_failed_path(file_path)
                failed_path.parent.mkdir(parents=True, exist_ok=True)

                source = processing_path if processing_path.exists() else file_path
                if source.exists():
                    shutil.move(str(source), str(failed_path))

                # Save error log
                error_log = failed_path.with_suffix('.error.log')
                with open(error_log, 'w') as f:
                    f.write(f"File: {file_path}\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Metadata: {metadata}\n")
                    f.write(f"Error: {str(e)}\n")
                    import traceback
                    f.write(f"\nTraceback:\n{traceback.format_exc()}\n")

                self.logger.info(f"Moved to failed: {failed_path}")
            except Exception as move_error:
                self.logger.error(f"Failed to move to failed directory: {move_error}")

        finally:
            self.processing_files.discard(str(file_path))


def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stdf_ingestion.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='STDF Watchdog Ingestion with State Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Monitors top-level incoming directory recursively for all facilities.

Directory Structure:
  incoming/{FACILITY}/{LOT}/{PRODUCT}/{TEST_PROGRAM}/*.stdf

Example:
  incoming/OSBE25/KEWGBCLD1U/HRG3301Y.06/Prod_TPP202_03/file.stdf
  incoming/OSBE26/LOT002/PRODUCT_B/TEST_V2/file.stdf

State Management:
  - File movement: incoming → processing → processed/failed
  - Database tracking: processed_files table (prevents duplicates)
  - Duplicate detection: Same file hash → moved to duplicates/

Usage:
  python watchdog_ingestion_stateful.py --base-path /data/stdf-ingestion
        """
    )

    parser.add_argument('--base-path', default='/data/stdf-ingestion',
                       help='Base directory (default: /data/stdf-ingestion)')
    parser.add_argument('--clickhouse-host', default='localhost',
                       help='ClickHouse host (default: localhost)')
    parser.add_argument('--clickhouse-port', type=int, default=9000,
                       help='ClickHouse port (default: 9000)')
    parser.add_argument('--no-db-tracking', action='store_true',
                       help='Disable database state tracking (file movement only)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Initialize configuration
    config = STDFIngestionConfig(args.base_path)
    logger.info(f"Initialized ingestion directories at: {config.base_path}")
    logger.info(f"  Incoming: {config.incoming}")
    logger.info(f"  Processing: {config.processing}")
    logger.info(f"  Processed: {config.processed}")
    logger.info(f"  Failed: {config.failed}")
    logger.info(f"  Duplicates: {config.duplicates}")

    # Initialize state tracker
    use_db = not args.no_db_tracking
    state_tracker = ProcessingStateTracker(
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port,
        use_database=use_db
    )

    if state_tracker.use_database:
        logger.info("Database state tracking ENABLED (duplicate detection active)")
    else:
        logger.info("Database state tracking DISABLED (file movement only)")

    # Create event handler
    event_handler = STDFFileHandler(
        config,
        state_tracker,
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port
    )

    # Setup watchdog observer
    # MONITOR TOP LEVEL RECURSIVELY - detects all OSBE25, OSBE26, etc.
    observer = Observer()
    observer.schedule(event_handler, str(config.incoming), recursive=True)
    observer.start()

    logger.info(f"Started watching: {config.incoming}")
    logger.info(f"Monitoring mode: RECURSIVE (all facilities auto-detected)")
    logger.info(f"Expected structure: {config.incoming}/FACILITY/LOT/PRODUCT/PROGRAM/*.stdf")
    logger.info(f"ClickHouse: {args.clickhouse_host}:{args.clickhouse_port}")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        observer.stop()

    observer.join()
    logger.info("Stopped")


if __name__ == '__main__':
    main()
