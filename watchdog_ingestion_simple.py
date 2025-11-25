#!/usr/bin/env python3
"""
STDF File Watchdog Ingestion - Filename-Based Metadata Extraction

Optimized for STDF files with embedded metadata in filename:
Format: {FACILITY}_{LOT}_{PRODUCT}_{LOT}_{PROGRAM}_{TESTER}_{TEMP}_{ID}_{TIMESTAMP}.stdf

Example:
OSBE25_KEWGBCLD1U_BE_HRG3301Y.06_KEWGBCLD1U__Prod_TPP202_03_Agilent_93000MT9510_25C_5264_2_20240903225947.stdf

Directory Structure Options:
1. Minimal: incoming/{FACILITY}/*.stdf
2. Date-based: incoming/{FACILITY}/{YYYY-MM-DD}/*.stdf
3. Flat: incoming/*.stdf
"""

import os
import sys
import re
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Import existing STDF processing modules
from extract_all_measurements import extract_all_measurements
from clickhouse_utils import push_to_clickhouse


class STDFFilenameParser:
    """Parse metadata from STDF filename convention"""

    # Filename pattern (flexible to handle variations)
    PATTERN = re.compile(
        r'^(?P<facility>[A-Z0-9]+)_'  # OSBE25
        r'(?P<lot>[A-Z0-9]+)_'         # KEWGBCLD1U
        r'(?P<product>[A-Z0-9_.]+)_'   # BE_HRG3301Y.06
        r'(?:[A-Z0-9]+_)?_?'           # Optional duplicate lot or empty field
        r'(?P<program>[A-Za-z0-9_]+)_' # Prod_TPP202_03
        r'(?P<tester>[A-Za-z0-9_]+)_'  # Agilent_93000MT9510
        r'(?P<temp>[0-9]+C)_'          # 25C
        r'(?P<seq>[0-9_]+)_'           # 5264_2
        r'(?P<timestamp>[0-9]{14})'    # 20240903225947
        r'\.stdf$',
        re.IGNORECASE
    )

    @classmethod
    def parse(cls, filename: str) -> Optional[Dict[str, str]]:
        """
        Parse metadata from STDF filename

        Args:
            filename: STDF filename (with or without path)

        Returns:
            Dict with keys: facility, lot, product, program, tester, temp, sequence, timestamp
            Returns None if filename doesn't match pattern
        """
        basename = os.path.basename(filename)
        match = cls.PATTERN.match(basename)

        if not match:
            return None

        metadata = match.groupdict()

        # Parse timestamp into datetime
        try:
            ts_str = metadata['timestamp']
            metadata['datetime'] = datetime.strptime(ts_str, '%Y%m%d%H%M%S')
            metadata['date'] = metadata['datetime'].strftime('%Y-%m-%d')
        except (ValueError, KeyError):
            metadata['datetime'] = None
            metadata['date'] = None

        return metadata

    @classmethod
    def is_valid_stdf_filename(cls, filename: str) -> bool:
        """Check if filename matches STDF naming convention"""
        return cls.parse(filename) is not None


class STDFIngestionConfig:
    """Configuration for STDF ingestion with flexible hierarchy"""

    def __init__(self, base_path: str = "/data/stdf-ingestion",
                 hierarchy: str = "facility-date"):
        """
        Initialize ingestion configuration

        Args:
            base_path: Root directory for ingestion
            hierarchy: Organization strategy:
                - "facility": incoming/{FACILITY}/*.stdf
                - "facility-date": incoming/{FACILITY}/{YYYY-MM-DD}/*.stdf
                - "flat": incoming/*.stdf
        """
        self.base_path = Path(base_path)
        self.hierarchy = hierarchy
        self.incoming = self.base_path / "incoming"
        self.processing = self.base_path / "processing"
        self.processed = self.base_path / "processed"
        self.failed = self.base_path / "failed"

        # Create directories
        for path in [self.incoming, self.processing, self.processed, self.failed]:
            path.mkdir(parents=True, exist_ok=True)

    def get_incoming_path_for_file(self, metadata: Dict[str, str]) -> Path:
        """Get appropriate incoming path based on hierarchy setting"""
        if self.hierarchy == "flat":
            return self.incoming
        elif self.hierarchy == "facility":
            return self.incoming / metadata['facility']
        elif self.hierarchy == "facility-date":
            return self.incoming / metadata['facility'] / metadata['date']
        else:
            raise ValueError(f"Unknown hierarchy: {self.hierarchy}")

    def get_processed_path(self, file_path: Path, metadata: Dict[str, str]) -> Path:
        """Get processed path with date-based archiving"""
        now = datetime.now()
        date_path = Path(str(now.year)) / f"{now.month:02d}" / f"{now.day:02d}"

        # Preserve incoming hierarchy + add date subdirectory
        if self.hierarchy == "flat":
            return self.processed / metadata['facility'] / date_path / file_path.name
        elif self.hierarchy == "facility":
            return self.processed / metadata['facility'] / date_path / file_path.name
        elif self.hierarchy == "facility-date":
            return self.processed / metadata['facility'] / metadata['date'] / date_path / file_path.name

        return self.processed / date_path / file_path.name

    def get_processing_path(self, file_path: Path, metadata: Dict[str, str]) -> Path:
        """Get processing path"""
        if self.hierarchy == "flat":
            return self.processing / file_path.name
        elif self.hierarchy == "facility":
            return self.processing / metadata['facility'] / file_path.name
        else:
            return self.processing / metadata['facility'] / metadata['date'] / file_path.name

    def get_failed_path(self, file_path: Path, metadata: Dict[str, str]) -> Path:
        """Get failed path"""
        if self.hierarchy == "flat":
            return self.failed / file_path.name
        elif self.hierarchy == "facility":
            return self.failed / metadata['facility'] / file_path.name
        else:
            return self.failed / metadata['facility'] / metadata['date'] / file_path.name


class STDFFileHandler(FileSystemEventHandler):
    """Handles STDF file events with filename-based metadata extraction"""

    def __init__(self, config: STDFIngestionConfig,
                 clickhouse_host: str = "localhost",
                 clickhouse_port: int = 9000):
        self.config = config
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.logger = logging.getLogger(__name__)
        self.processing_files = set()

    def on_created(self, event):
        """Called when file is created"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .stdf files
        if file_path.suffix.lower() != '.stdf':
            return

        # Parse filename to validate format
        metadata = STDFFilenameParser.parse(file_path.name)
        if not metadata:
            self.logger.warning(f"Filename doesn't match expected pattern: {file_path.name}")
            self.logger.warning("Expected format: FACILITY_LOT_PRODUCT_..._PROGRAM_TESTER_TEMP_SEQ_TIMESTAMP.stdf")
            # Still process it, but with limited metadata
            metadata = {'facility': 'UNKNOWN', 'lot': 'UNKNOWN', 'product': 'UNKNOWN',
                       'program': 'UNKNOWN', 'date': datetime.now().strftime('%Y-%m-%d')}

        # Wait for file stability
        self._wait_for_file_stable(file_path)

        # Process the file
        self.process_stdf_file(file_path, metadata)

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

    def process_stdf_file(self, file_path: Path, metadata: Dict[str, str]):
        """Process STDF file through ingestion pipeline"""

        if str(file_path) in self.processing_files:
            self.logger.info(f"File already being processed: {file_path}")
            return

        self.processing_files.add(str(file_path))

        try:
            self.logger.info(f"Starting ingestion: {file_path}")
            self.logger.info(f"Metadata: Facility={metadata.get('facility')}, "
                           f"Lot={metadata.get('lot')}, Product={metadata.get('product')}, "
                           f"Program={metadata.get('program')}")

            # Step 1: Move to processing
            processing_path = self.config.get_processing_path(file_path, metadata)
            processing_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(processing_path))
            self.logger.info(f"Moved to processing: {processing_path}")

            # Step 2: Parse STDF
            self.logger.info(f"Parsing STDF file...")
            measurements_df = extract_all_measurements(str(processing_path))

            if measurements_df.empty:
                raise ValueError("No measurements extracted from STDF file")

            self.logger.info(f"Extracted {len(measurements_df)} measurements")

            # Step 3: Push to ClickHouse
            self.logger.info(f"Pushing to ClickHouse: {self.clickhouse_host}:{self.clickhouse_port}")
            push_to_clickhouse(
                measurements_df,
                host=self.clickhouse_host,
                port=self.clickhouse_port
            )
            self.logger.info(f"Successfully pushed {len(measurements_df)} records")

            # Step 4: Move to processed
            processed_path = self.config.get_processed_path(processing_path, metadata)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(processing_path), str(processed_path))
            self.logger.info(f"Moved to processed: {processed_path}")

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}", exc_info=True)

            try:
                failed_path = self.config.get_failed_path(file_path, metadata)
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
        description='STDF Watchdog Ingestion with Filename-Based Metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Directory Hierarchy Options:
  --hierarchy flat           incoming/*.stdf (all files in one directory)
  --hierarchy facility       incoming/{FACILITY}/*.stdf (organize by facility)
  --hierarchy facility-date  incoming/{FACILITY}/{YYYY-MM-DD}/*.stdf (default)

Examples:
  # Facility + Date organization (recommended)
  python watchdog_ingestion_simple.py --hierarchy facility-date

  # Facility only (simpler)
  python watchdog_ingestion_simple.py --hierarchy facility

  # Flat (simplest, but may have performance issues with many files)
  python watchdog_ingestion_simple.py --hierarchy flat
        """
    )

    parser.add_argument('--base-path', default='/data/stdf-ingestion',
                       help='Base directory (default: /data/stdf-ingestion)')
    parser.add_argument('--hierarchy', default='facility-date',
                       choices=['flat', 'facility', 'facility-date'],
                       help='Directory organization (default: facility-date)')
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
    config = STDFIngestionConfig(args.base_path, args.hierarchy)
    logger.info(f"Initialized ingestion with hierarchy: {args.hierarchy}")
    logger.info(f"Watching: {config.incoming}")

    # Create event handler
    event_handler = STDFFileHandler(
        config,
        clickhouse_host=args.clickhouse_host,
        clickhouse_port=args.clickhouse_port
    )

    # Setup watchdog
    observer = Observer()
    observer.schedule(event_handler, str(config.incoming), recursive=True)
    observer.start()

    logger.info(f"Started watching: {config.incoming}")
    logger.info(f"Hierarchy mode: {args.hierarchy}")
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
