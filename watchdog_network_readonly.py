#!/usr/bin/env python3
"""
STDF Watchdog Ingestion - READ-ONLY Network Folder Monitoring

Monitors a READ-ONLY network folder for STDF files and processes them locally.

Network Folder Structure (READ ONLY):
    /mnt/network/stdf/
    ├── OSBE25/
    │   └── KEWGBCLD1U/
    │       └── HRG3301Y.06/
    │           └── Prod_TPP202_03/
    │               └── *.stdf
    ├── OSBE26/
    └── OSBE27/

Features:
- Monitors read-only network folder recursively
- Processes existing files on startup (initial scan)
- Watches for new files (event-driven)
- Database-only state tracking (no file movement on network)
- Local working directory for processing
- Handles dynamic facility structure

State Tracking:
- Database hash tracking (processed_files table)
- No file movement on network folder (read-only)
- Local logs and error tracking
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

try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    ClickHouseClient = None


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file for deduplication"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class NetworkFileStateTracker:
    """Tracks processed files via database (for read-only network folders)"""

    def __init__(self, clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000):
        self.logger = logging.getLogger(__name__)
        self.processed_hashes: Set[str] = set()
        self.client = None

        try:
            self.client = ClickHouseClient(host=clickhouse_host, port=clickhouse_port)
            self._ensure_tracking_table()
            self._load_processed_hashes()
            self.logger.info("Database state tracking initialized")
        except Exception as e:
            self.logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def _ensure_tracking_table(self):
        """Verify measurements table exists (already has file_hash field)"""
        try:
            # Check if measurements table exists
            self.client.execute("SELECT COUNT(*) FROM measurements LIMIT 1")
            self.logger.info("Using existing measurements table for file_hash tracking")
        except Exception as e:
            self.logger.warning(f"Measurements table not found: {e}")
            self.logger.info("Will be created when first file is processed")

    def _load_processed_hashes(self):
        """Load all processed file hashes into memory from measurements table"""
        try:
            query = "SELECT DISTINCT file_hash FROM measurements WHERE file_hash != ''"
            result = self.client.execute(query)
            self.processed_hashes = {row[0] for row in result if row[0]}
            self.logger.info(f"Loaded {len(self.processed_hashes)} processed file hashes from measurements table")
        except Exception as e:
            self.logger.warning(f"Could not load processed hashes: {e}")
            self.processed_hashes = set()

    def is_processed(self, file_hash: str) -> bool:
        """Check if file has been processed"""
        return file_hash in self.processed_hashes

    def mark_completed(self, file_hash: str):
        """Add file hash to processed set (already in measurements table from push_to_clickhouse)"""
        self.processed_hashes.add(file_hash)
        self.logger.debug(f"Marked hash as processed: {file_hash[:16]}...")


class NetworkFolderConfig:
    """Configuration for read-only network folder monitoring"""

    def __init__(self, network_path: str, local_work_dir: str = "/tmp/stdf-processing"):
        self.network_path = Path(network_path)
        self.local_work_dir = Path(local_work_dir)

        # Create local working directories
        self.local_processing = self.local_work_dir / "processing"
        self.local_failed = self.local_work_dir / "failed"
        self.local_logs = self.local_work_dir / "logs"

        for path in [self.local_processing, self.local_failed, self.local_logs]:
            path.mkdir(parents=True, exist_ok=True)

    def extract_metadata_from_path(self, file_path: Path) -> Dict[str, str]:
        """
        Extract metadata from network folder structure

        Expected: network_path/FACILITY/LOT/PRODUCT/TEST_PROGRAM/file.stdf
        """
        try:
            rel_path = file_path.relative_to(self.network_path)
            parts = rel_path.parts

            metadata = {
                'facility': parts[0] if len(parts) > 1 else 'UNKNOWN',
                'lot': parts[1] if len(parts) > 2 else 'UNKNOWN',
                'product': parts[2] if len(parts) > 3 else 'UNKNOWN',
                'test_program': parts[3] if len(parts) > 4 else 'UNKNOWN',
            }
        except ValueError:
            metadata = {
                'facility': 'UNKNOWN',
                'lot': 'UNKNOWN',
                'product': 'UNKNOWN',
                'test_program': 'UNKNOWN',
            }

        return metadata

    def get_local_processing_path(self, network_file_path: Path) -> Path:
        """Get local path for processing (copy from network)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self.local_processing / f"{network_file_path.stem}_{timestamp}{network_file_path.suffix}"


class NetworkSTDFFileHandler(FileSystemEventHandler):
    """Handles STDF files from read-only network folder"""

    def __init__(self, config: NetworkFolderConfig,
                 state_tracker: NetworkFileStateTracker,
                 clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000):
        self.config = config
        self.state_tracker = state_tracker
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.logger = logging.getLogger(__name__)
        self.processing_files = set()

    def on_created(self, event):
        """Called when new file appears on network folder"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .stdf files
        if file_path.suffix.lower() != '.stdf':
            return

        # Wait for file to be completely written
        self._wait_for_file_stable(file_path)

        # Process the file
        self.process_network_file(file_path)

    def on_modified(self, event):
        """Called when file is modified (useful for network sync delays)"""
        # Treat modified as potential new file
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() == '.stdf':
                self._wait_for_file_stable(file_path)
                self.process_network_file(file_path)

    def _wait_for_file_stable(self, file_path: Path, timeout: int = 30):
        """Wait for file size to stabilize"""
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

    def process_network_file(self, network_file_path: Path):
        """Process STDF file from network folder"""

        # Prevent concurrent processing
        if str(network_file_path) in self.processing_files:
            return

        self.processing_files.add(str(network_file_path))

        local_file_path = None

        try:
            # Extract metadata from network path
            metadata = self.config.extract_metadata_from_path(network_file_path)
            self.logger.info(f"Processing: {network_file_path}")
            self.logger.info(f"Metadata: Facility={metadata['facility']}, "
                           f"Lot={metadata['lot']}, Product={metadata['product']}, "
                           f"Program={metadata['test_program']}")

            # Calculate file hash
            file_hash = calculate_file_hash(str(network_file_path))
            self.logger.debug(f"File hash: {file_hash}")

            # Check if already processed
            if self.state_tracker.is_processed(file_hash):
                self.logger.info(f"SKIPPED: Already processed (hash: {file_hash[:16]}...)")
                return

            # Copy to local processing directory
            local_file_path = self.config.get_local_processing_path(network_file_path)
            self.logger.debug(f"Copying to local: {local_file_path}")
            shutil.copy2(str(network_file_path), str(local_file_path))

            # Parse STDF file (from local copy)
            self.logger.info(f"Parsing STDF file...")
            measurements_df = extract_all_measurements(str(local_file_path))

            if measurements_df.empty:
                raise ValueError("No measurements extracted from STDF file")

            self.logger.info(f"Extracted {len(measurements_df)} measurements")

            # Push to ClickHouse
            self.logger.info(f"Pushing to ClickHouse: {self.clickhouse_host}:{self.clickhouse_port}")
            push_to_clickhouse(
                measurements_df,
                host=self.clickhouse_host,
                port=self.clickhouse_port
            )
            self.logger.info(f"Successfully pushed {len(measurements_df)} records")

            # Mark as completed (add to in-memory cache)
            # Note: file_hash already in measurements table from push_to_clickhouse
            self.state_tracker.mark_completed(file_hash)
            self.logger.info(f"Completed: {network_file_path}")

            # Clean up local copy
            if local_file_path and local_file_path.exists():
                local_file_path.unlink()

        except Exception as e:
            self.logger.error(f"Error processing {network_file_path}: {e}", exc_info=True)
            # Note: Failed files won't have hash in measurements table, so will retry next time

            # Save error log locally
            try:
                error_log = self.config.local_failed / f"{network_file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.error.log"
                with open(error_log, 'w') as f:
                    f.write(f"Network File: {network_file_path}\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Metadata: {metadata}\n")
                    f.write(f"Error: {str(e)}\n")
                    import traceback
                    f.write(f"\nTraceback:\n{traceback.format_exc()}\n")
                self.logger.info(f"Error log saved: {error_log}")

                # Move failed local copy to failed directory
                if local_file_path and local_file_path.exists():
                    failed_copy = self.config.local_failed / local_file_path.name
                    shutil.move(str(local_file_path), str(failed_copy))
            except Exception as log_error:
                self.logger.error(f"Failed to save error log: {log_error}")

        finally:
            self.processing_files.discard(str(network_file_path))

            # Cleanup local file if still exists
            if local_file_path and local_file_path.exists():
                try:
                    local_file_path.unlink()
                except:
                    pass


def scan_existing_files(network_path: Path, handler: NetworkSTDFFileHandler):
    """Initial scan of existing files on network folder"""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting initial scan of existing files in: {network_path}")

    stdf_files = list(network_path.rglob("*.stdf"))
    logger.info(f"Found {len(stdf_files)} existing STDF files")

    processed_count = 0
    skipped_count = 0

    for file_path in stdf_files:
        try:
            # Check if already processed
            file_hash = calculate_file_hash(str(file_path))
            if handler.state_tracker.is_processed(file_hash):
                skipped_count += 1
                logger.debug(f"Skipped (already processed): {file_path}")
            else:
                handler.process_network_file(file_path)
                processed_count += 1
        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")

    logger.info(f"Initial scan complete: {processed_count} processed, {skipped_count} skipped (already done)")


def setup_logging(log_dir: Path, log_level: str = "INFO"):
    """Configure logging"""
    log_file = log_dir / f"stdf_ingestion_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='STDF Watchdog - READ-ONLY Network Folder Monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Monitors a READ-ONLY network folder for STDF files.

Network Folder Structure:
  /mnt/network/stdf/OSBE25/LOT/PRODUCT/PROGRAM/*.stdf

Features:
  - Processes existing files on startup (initial scan)
  - Watches for new files (event-driven)
  - Database-only state tracking (no file movement on network)
  - Local working directory for processing

Usage:
  # Mount network folder first
  sudo mount -t cifs //server/share /mnt/network/stdf -o ro,username=user

  # Start watchdog
  python watchdog_network_readonly.py \\
      --network-path /mnt/network/stdf \\
      --local-work-dir /tmp/stdf-processing

  # Or for local testing
  python watchdog_network_readonly.py \\
      --network-path ./STDF_Files
        """
    )

    parser.add_argument('--network-path', required=True,
                       help='Network folder path (READ ONLY)')
    parser.add_argument('--local-work-dir', default='/tmp/stdf-processing',
                       help='Local working directory (default: /tmp/stdf-processing)')
    parser.add_argument('--clickhouse-host', default='localhost',
                       help='ClickHouse host (default: localhost)')
    parser.add_argument('--clickhouse-port', type=int, default=9000,
                       help='ClickHouse port (default: 9000)')
    parser.add_argument('--skip-initial-scan', action='store_true',
                       help='Skip scanning existing files (only watch for new files)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')

    args = parser.parse_args()

    # Initialize configuration
    config = NetworkFolderConfig(args.network_path, args.local_work_dir)

    # Setup logging
    setup_logging(config.local_logs, args.log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("STDF Watchdog - Network Folder Monitoring (READ ONLY)")
    logger.info("=" * 70)
    logger.info(f"Network Path: {config.network_path}")
    logger.info(f"Local Work Dir: {config.local_work_dir}")
    logger.info(f"ClickHouse: {args.clickhouse_host}:{args.clickhouse_port}")

    # Verify network path exists
    if not config.network_path.exists():
        logger.error(f"Network path does not exist: {config.network_path}")
        sys.exit(1)

    # Initialize state tracker
    try:
        state_tracker = NetworkFileStateTracker(
            clickhouse_host=args.clickhouse_host,
            clickhouse_port=args.clickhouse_port
        )
    except Exception as e:
        logger.error(f"Failed to initialize state tracker: {e}")
        sys.exit(1)

    # Create event handler
    event_handler = NetworkSTDFFileHandler(
        config,
        state_tracker,
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port
    )

    # Initial scan of existing files
    if not args.skip_initial_scan:
        scan_existing_files(config.network_path, event_handler)
    else:
        logger.info("Skipping initial scan (--skip-initial-scan)")

    # Setup watchdog observer for new files
    observer = Observer()
    observer.schedule(event_handler, str(config.network_path), recursive=True)
    observer.start()

    logger.info(f"Started watching: {config.network_path}")
    logger.info("Monitoring mode: RECURSIVE (all facilities auto-detected)")
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
