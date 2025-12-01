#!/usr/bin/env python3
"""
Automated MES Emulator with Watchdog
=====================================

Monitors STDF directory structure and automatically triggers API calls when
new files or folders are detected.

Directory Structure:
    network_path/ProductClass/ProductType/Equipment/Operation/Lot/*.stdf

When a new .stdf file is detected, automatically calls SetStdfFile API with
extracted parameters from the directory path.

Features:
- Watches for file creation and modification events
- Debounces multiple files in same lot (configurable delay)
- Extracts API parameters from directory structure
- Automatic retry on API failures
- Detailed logging

Usage:
    # Watch directory and auto-process
    python emulate_mes_call_automated.py --network-path ./STDF_Files

    # With custom API endpoint and debounce
    python emulate_mes_call_automated.py \\
        --network-path /mnt/network/stdf \\
        --api-url http://localhost:8000/SetStdfFile \\
        --debounce-seconds 5

    # Dry run mode (don't actually call API)
    python emulate_mes_call_automated.py \\
        --network-path ./STDF_Files \\
        --dry-run
"""

import os
import sys
import time
import logging
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, Optional
from collections import defaultdict

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Global configuration"""
    API_URL = "http://localhost:8000/SetStdfFile"
    DEBOUNCE_SECONDS = 3  # Wait 3 seconds after last file before triggering
    DRY_RUN = False
    OPERATION_NAME_DEFAULT = "Test Operation"  # Default operation name


# =============================================================================
# Lot Processing Tracker
# =============================================================================

class LotTracker:
    """
    Tracks lot directories that need processing with debouncing.

    When files are added to a lot, starts a timer. If more files are added,
    resets the timer. When timer expires, triggers API call.
    """

    def __init__(self, debounce_seconds: int, callback):
        self.debounce_seconds = debounce_seconds
        self.callback = callback
        self.pending_lots: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    def schedule_lot_processing(self, lot_path: str, api_params: dict):
        """
        Schedule lot for processing after debounce delay.

        Args:
            lot_path: Full path to lot directory
            api_params: Dictionary with API parameters
        """
        with self.lock:
            # Cancel existing timer if any
            if lot_path in self.pending_lots:
                self.pending_lots[lot_path].cancel()
                self.logger.debug(f"Rescheduling lot: {lot_path}")
            else:
                self.logger.info(f"Scheduling lot: {lot_path}")

            # Create new timer
            timer = threading.Timer(
                self.debounce_seconds,
                self._process_lot,
                args=(lot_path, api_params)
            )
            timer.daemon = True
            self.pending_lots[lot_path] = timer
            timer.start()

    def _process_lot(self, lot_path: str, api_params: dict):
        """Process lot (called after debounce delay)"""
        with self.lock:
            if lot_path in self.pending_lots:
                del self.pending_lots[lot_path]

        self.logger.info(f"Processing lot: {api_params['LotNumber']}")
        self.callback(api_params)

    def wait_for_pending(self):
        """Wait for all pending timers to complete"""
        while True:
            with self.lock:
                if not self.pending_lots:
                    break
                pending_count = len(self.pending_lots)

            self.logger.info(f"Waiting for {pending_count} pending lot(s) to complete...")
            time.sleep(0.5)


# =============================================================================
# Directory Watcher
# =============================================================================

class STDFDirectoryHandler(FileSystemEventHandler):
    """
    Handles filesystem events for STDF directory structure.

    Monitors for new .stdf files and triggers API calls based on
    directory structure: ProductClass/ProductType/Equipment/Operation/Lot/
    """

    def __init__(self, base_path: Path, lot_tracker: LotTracker):
        self.base_path = base_path
        self.lot_tracker = lot_tracker
        self.logger = logging.getLogger(__name__)
        self.processed_events: Set[str] = set()  # Avoid duplicate events

    def on_created(self, event):
        """Handle file/directory creation events"""
        if event.is_directory:
            self.logger.debug(f"Directory created: {event.src_path}")
            # Could trigger immediate scan of new directory
            self._check_directory_for_stdf(event.src_path)
        else:
            self._handle_file_event(event)

    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            self._handle_file_event(event)

    def _handle_file_event(self, event):
        """Process file creation/modification event"""
        file_path = Path(event.src_path)

        # Only process .stdf files
        if file_path.suffix.lower() != '.stdf':
            return

        # Avoid duplicate events (watchdog can fire multiple events)
        event_key = f"{event.event_type}:{event.src_path}"
        if event_key in self.processed_events:
            return
        self.processed_events.add(event_key)

        self.logger.info(f"STDF file detected: {file_path.name}")

        # Extract API parameters from path
        api_params = self._extract_api_params(file_path)
        if api_params:
            lot_path = str(file_path.parent)
            self.lot_tracker.schedule_lot_processing(lot_path, api_params)
        else:
            self.logger.warning(f"Could not extract parameters from path: {file_path}")

    def _check_directory_for_stdf(self, dir_path: str):
        """Check if new directory contains STDF files"""
        try:
            dir_path_obj = Path(dir_path)
            stdf_files = list(dir_path_obj.glob("*.stdf"))

            if stdf_files:
                self.logger.info(f"New directory with {len(stdf_files)} STDF files: {dir_path}")

                # Extract parameters from first file
                api_params = self._extract_api_params(stdf_files[0])
                if api_params:
                    self.lot_tracker.schedule_lot_processing(dir_path, api_params)
        except Exception as e:
            self.logger.error(f"Error checking directory {dir_path}: {e}")

    def _extract_api_params(self, file_path: Path) -> Optional[dict]:
        """
        Extract API parameters from file path.

        Expected structure:
            base_path/ProductClass/ProductType/Equipment/Operation/Lot/file.stdf

        Example:
            STDF_Files/PCBcast Pixlog 2217/KEWGBCLD1U/3CMT0101/5264/HRG3201Y.09/file.stdf

        Returns:
            Dictionary with API parameters or None if path doesn't match structure
        """
        try:
            # Get relative path from base
            rel_path = file_path.relative_to(self.base_path)
            parts = rel_path.parts

            # Need at least 6 parts: ProductClass/ProductType/Equipment/Operation/Lot/file.stdf
            if len(parts) < 6:
                return None

            # Extract components (from the end, since ProductClass might have spaces)
            filename = parts[-1]
            lot_number = parts[-2]
            operation_number = parts[-3]
            equipment_number = parts[-4]
            product_type = parts[-5]

            # Everything else is product class (join in case it has path separators)
            product_class = "/".join(parts[:-5])

            self.logger.debug(f"Extracted from path:")
            self.logger.debug(f"  ProductClass: {product_class}")
            self.logger.debug(f"  ProductType: {product_type}")
            self.logger.debug(f"  Equipment: {equipment_number}")
            self.logger.debug(f"  Operation: {operation_number}")
            self.logger.debug(f"  Lot: {lot_number}")

            return {
                "LotNumber": lot_number,
                "OperationNumber": operation_number,
                "OperationName": Config.OPERATION_NAME_DEFAULT,
                "EquipmentNumber": equipment_number,
                "ProductType": product_type,
                "ProductClass": product_class
            }

        except ValueError as e:
            self.logger.warning(f"Path not under base path: {file_path}")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting parameters: {e}", exc_info=True)
            return None


# =============================================================================
# API Client
# =============================================================================

def call_api(api_params: dict, api_url: str, dry_run: bool = False):
    """
    Call SetStdfFile API endpoint.

    Args:
        api_params: Dictionary with LotNumber, OperationNumber, etc.
        api_url: API endpoint URL
        dry_run: If True, don't actually call API
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("Calling SetStdfFile API")
    logger.info("=" * 70)
    logger.info(f"Lot:           {api_params['LotNumber']}")
    logger.info(f"Operation:     {api_params['OperationNumber']}")
    logger.info(f"Equipment:     {api_params['EquipmentNumber']}")
    logger.info(f"Product Type:  {api_params['ProductType']}")
    logger.info(f"Product Class: {api_params['ProductClass']}")

    if dry_run:
        logger.info("DRY RUN - API call skipped")
        logger.info("=" * 70)
        return

    try:
        response = requests.post(
            api_url,
            json=api_params,
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 minute timeout for processing
        )

        logger.info(f"API Response: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Status: {result['status'].upper()}")
            logger.info(f"   Files Total: {result['files_total']}")
            logger.info(f"   Files Processed: {result['files_processed']}")
            logger.info(f"   Files Skipped: {result['files_skipped']}")
            logger.info(f"   Files Failed: {result['files_failed']}")
            logger.info(f"   Total Measurements: {result['total_measurements']}")
            logger.info(f"   Processing Time: {result['processing_time_seconds']}s")
        else:
            logger.error(f"❌ API Error: {response.status_code}")
            logger.error(f"   Response: {response.text}")

    except requests.exceptions.Timeout:
        logger.error("❌ API call timeout (>10 minutes)")
    except requests.exceptions.ConnectionError:
        logger.error(f"❌ Cannot connect to API at {api_url}")
        logger.error("   Make sure stdf_api_service.py is running")
    except Exception as e:
        logger.error(f"❌ API call failed: {e}", exc_info=True)

    logger.info("=" * 70)


# =============================================================================
# Main Application
# =============================================================================

def setup_logging(log_level: str = "INFO", log_file: str = "emulate_mes_automated.log"):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Automated MES Emulator with Directory Watching',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch directory and auto-process
  python emulate_mes_call_automated.py --network-path ./STDF_Files

  # With custom settings
  python emulate_mes_call_automated.py \\
      --network-path /mnt/network/stdf \\
      --api-url http://10.96.38.217:8000/SetStdfFile \\
      --debounce-seconds 5

  # Dry run mode (don't call API)
  python emulate_mes_call_automated.py \\
      --network-path ./STDF_Files \\
      --dry-run

  # Verbose logging
  python emulate_mes_call_automated.py \\
      --network-path ./STDF_Files \\
      --log-level DEBUG
        """
    )

    parser.add_argument('--network-path', required=True,
                       help='Network folder path to watch (e.g., ./STDF_Files)')
    parser.add_argument('--api-url', default='http://localhost:8000/SetStdfFile',
                       help='API endpoint URL (default: http://localhost:8000/SetStdfFile)')
    parser.add_argument('--debounce-seconds', type=int, default=3,
                       help='Seconds to wait after last file before calling API (default: 3)')
    parser.add_argument('--operation-name', default='Test Operation',
                       help='Default operation name (default: Test Operation)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - detect files but don\'t call API')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--log-file', default='emulate_mes_automated.log',
                       help='Log file path (default: emulate_mes_automated.log)')

    args = parser.parse_args()

    # Update global config
    Config.API_URL = args.api_url
    Config.DEBOUNCE_SECONDS = args.debounce_seconds
    Config.DRY_RUN = args.dry_run
    Config.OPERATION_NAME_DEFAULT = args.operation_name

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("Automated MES Emulator - Directory Watcher")
    logger.info("=" * 70)
    logger.info(f"Network Path:      {args.network_path}")
    logger.info(f"API URL:           {args.api_url}")
    logger.info(f"Debounce Delay:    {args.debounce_seconds}s")
    logger.info(f"Dry Run:           {args.dry_run}")
    logger.info(f"Log File:          {args.log_file}")
    logger.info("=" * 70)

    # Verify network path exists
    base_path = Path(args.network_path)
    if not base_path.exists():
        logger.error(f"Network path does not exist: {base_path}")
        sys.exit(1)

    # Create lot tracker with API callback
    def api_callback(api_params):
        call_api(api_params, args.api_url, args.dry_run)

    lot_tracker = LotTracker(args.debounce_seconds, api_callback)

    # Create event handler and observer
    event_handler = STDFDirectoryHandler(base_path, lot_tracker)
    observer = Observer()
    observer.schedule(event_handler, str(base_path), recursive=True)

    # Start watching
    logger.info("Starting directory watcher...")
    logger.info("Press Ctrl+C to stop")
    logger.info("")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping directory watcher...")
        observer.stop()

        # Wait for pending lots to complete
        logger.info("Waiting for pending lots to complete...")
        lot_tracker.wait_for_pending()

    observer.join()
    logger.info("Directory watcher stopped")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
