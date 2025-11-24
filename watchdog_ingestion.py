#!/usr/bin/env python3
"""
STDF File Watchdog Ingestion System

Monitors directory structure for new STDF files and automatically processes them.
Organizes files by: FACILITY/LOT/PRODUCT/TEST_PROGRAM

Directory Structure:
    incoming/{FACILITY}/{LOT}/{PRODUCT}/{TEST_PROGRAM}/*.stdf  ← Watchdog monitors here
    processing/{same structure}                                 ← Being processed
    processed/{same structure}/{YYYY}/{MM}/{DD}/*.stdf         ← Successfully ingested
    failed/{same structure}/*.stdf + error.log                 ← Parse errors
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Import your existing STDF processing modules
from extract_all_measurements import extract_all_measurements
from clickhouse_utils import push_to_clickhouse


class STDFIngestionConfig:
    """Configuration for STDF ingestion paths"""

    def __init__(self, base_path: str = "/data/stdf-ingestion"):
        self.base_path = Path(base_path)
        self.incoming = self.base_path / "incoming"
        self.processing = self.base_path / "processing"
        self.processed = self.base_path / "processed"
        self.failed = self.base_path / "failed"

        # Create all directories if they don't exist
        for path in [self.incoming, self.processing, self.processed, self.failed]:
            path.mkdir(parents=True, exist_ok=True)

    def get_relative_path(self, file_path: Path) -> Path:
        """Extract relative path from incoming directory"""
        try:
            return file_path.relative_to(self.incoming)
        except ValueError:
            # File not in incoming directory
            return Path(file_path.name)

    def get_processing_path(self, file_path: Path) -> Path:
        """Get processing directory path for file"""
        rel_path = self.get_relative_path(file_path)
        return self.processing / rel_path

    def get_processed_path(self, file_path: Path) -> Path:
        """Get processed directory path for file (with date partitioning)"""
        rel_path = self.get_relative_path(file_path)
        now = datetime.now()
        # Add YYYY/MM/DD subdirectories
        date_path = Path(str(now.year)) / f"{now.month:02d}" / f"{now.day:02d}"
        return self.processed / rel_path.parent / date_path / rel_path.name

    def get_failed_path(self, file_path: Path) -> Path:
        """Get failed directory path for file"""
        rel_path = self.get_relative_path(file_path)
        return self.failed / rel_path


class STDFFileHandler(FileSystemEventHandler):
    """Handles STDF file events for automated ingestion"""

    def __init__(self, config: STDFIngestionConfig,
                 clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000):
        self.config = config
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.logger = logging.getLogger(__name__)

        # Track files being processed to avoid duplicates
        self.processing_files = set()

    def on_created(self, event):
        """Called when a file is created in the watched directory"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .stdf files
        if file_path.suffix.lower() != '.stdf':
            return

        # Wait for file to be completely written (avoid partial reads)
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

        while stable_count < 3:  # Require 3 consecutive same-size checks
            if time.time() - start_time > timeout:
                self.logger.warning(f"Timeout waiting for file to stabilize: {file_path}")
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
        """Process a single STDF file through the ingestion pipeline"""

        # Avoid processing the same file twice
        if str(file_path) in self.processing_files:
            self.logger.info(f"File already being processed: {file_path}")
            return

        self.processing_files.add(str(file_path))

        try:
            self.logger.info(f"Starting ingestion: {file_path}")

            # Step 1: Move to processing directory
            processing_path = self.config.get_processing_path(file_path)
            processing_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(processing_path))
            self.logger.info(f"Moved to processing: {processing_path}")

            # Step 2: Extract metadata from directory structure
            metadata = self._extract_metadata_from_path(processing_path)
            self.logger.info(f"Extracted metadata: {metadata}")

            # Step 3: Parse STDF file
            self.logger.info(f"Parsing STDF file: {processing_path}")
            measurements_df = extract_all_measurements(str(processing_path))

            if measurements_df.empty:
                raise ValueError("No measurements extracted from STDF file")

            self.logger.info(f"Extracted {len(measurements_df)} measurements")

            # Step 4: Push to ClickHouse
            self.logger.info(f"Pushing to ClickHouse: {self.clickhouse_host}:{self.clickhouse_port}")
            push_to_clickhouse(
                measurements_df,
                host=self.clickhouse_host,
                port=self.clickhouse_port
            )
            self.logger.info(f"Successfully pushed {len(measurements_df)} records to ClickHouse")

            # Step 5: Move to processed directory
            processed_path = self.config.get_processed_path(processing_path)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(processing_path), str(processed_path))
            self.logger.info(f"Moved to processed: {processed_path}")

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)

            # Move to failed directory and save error log
            try:
                failed_path = self.config.get_failed_path(file_path)
                failed_path.parent.mkdir(parents=True, exist_ok=True)

                # Move file (from processing or original location)
                source = processing_path if processing_path.exists() else file_path
                if source.exists():
                    shutil.move(str(source), str(failed_path))

                # Save error log
                error_log = failed_path.with_suffix('.error.log')
                with open(error_log, 'w') as f:
                    f.write(f"File: {file_path}\n")
                    f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                    f.write(f"Error: {str(e)}\n")
                    import traceback
                    f.write(f"\nTraceback:\n{traceback.format_exc()}\n")

                self.logger.info(f"Moved to failed: {failed_path}")
            except Exception as move_error:
                self.logger.error(f"Failed to move file to failed directory: {move_error}")

        finally:
            self.processing_files.discard(str(file_path))

    def _extract_metadata_from_path(self, file_path: Path) -> Dict[str, str]:
        """
        Extract metadata from directory structure

        Expected path: incoming/FACILITY/LOT/PRODUCT/TEST_PROGRAM/filename.stdf

        Returns:
            Dict with keys: facility, lot, product, test_program
        """
        rel_path = self.config.get_relative_path(file_path)
        parts = rel_path.parts

        metadata = {
            'facility': None,
            'lot': None,
            'product': None,
            'test_program': None,
        }

        # Extract from directory hierarchy (skip filename)
        if len(parts) > 1:
            metadata['facility'] = parts[0]
        if len(parts) > 2:
            metadata['lot'] = parts[1]
        if len(parts) > 3:
            metadata['product'] = parts[2]
        if len(parts) > 4:
            metadata['test_program'] = parts[3]

        return metadata


def setup_logging(log_level: str = "INFO"):
    """Configure logging for the ingestion system"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('stdf_ingestion.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point for STDF watchdog ingestion"""
    import argparse

    parser = argparse.ArgumentParser(description='STDF File Watchdog Ingestion System')
    parser.add_argument('--base-path', default='/data/stdf-ingestion',
                        help='Base directory for ingestion (default: /data/stdf-ingestion)')
    parser.add_argument('--clickhouse-host', default='localhost',
                        help='ClickHouse host (default: localhost)')
    parser.add_argument('--clickhouse-port', type=int, default=9000,
                        help='ClickHouse port (default: 9000)')
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

    # Create event handler
    event_handler = STDFFileHandler(
        config,
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port
    )

    # Setup watchdog observer
    observer = Observer()
    observer.schedule(event_handler, str(config.incoming), recursive=True)
    observer.start()

    logger.info(f"Started watching: {config.incoming}")
    logger.info(f"ClickHouse target: {args.clickhouse_host}:{args.clickhouse_port}")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watchdog observer...")
        observer.stop()

    observer.join()
    logger.info("Watchdog observer stopped")


if __name__ == '__main__':
    main()
