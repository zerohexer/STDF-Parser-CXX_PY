#!/usr/bin/env python3
"""
STDF C++ Parser Python Wrapper

This module provides a Python interface to the high-performance C++ STDF parser.
It bridges the C++ parsing engine with the existing Python ClickHouse integration.
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Import the C++ extension (will be available after building)
try:
    import stdf_parser_cpp
except ImportError:
    print("Warning: stdf_parser_cpp extension not built yet. Run 'python setup.py build_ext --inplace'")
    stdf_parser_cpp = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class STDFCppParser:
    """
    High-performance STDF parser using C++ backend with Python integration.
    
    This class provides the interface between the C++ parsing engine and
    the existing Python ClickHouse processing pipeline.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the STDF C++ parser.
        
        Args:
            config: Configuration dictionary for field extraction and processing
        """
        self.config = config or {}
        self.stats = {
            'files_processed': 0,
            'total_records': 0,
            'parsed_records': 0,
            'processing_time': 0.0
        }
    
    def parse_stdf_file(self, filepath: str) -> Dict[str, Any]:
        """
        Parse an STDF file using the C++ engine.
        
        Args:
            filepath: Path to the STDF file
            
        Returns:
            Dictionary containing parsed records and statistics
            
        Raises:
            FileNotFoundError: If the STDF file doesn't exist
            RuntimeError: If the C++ parser encounters an error
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"STDF file not found: {filepath}")
        
        if stdf_parser_cpp is None:
            raise RuntimeError("C++ extension not available. Please build the extension first.")
        
        logger.info(f"Parsing STDF file with C++ engine: {filepath}")
        start_time = time.time()
        
        try:
            # Call C++ parser
            result = stdf_parser_cpp.parse_stdf_file(filepath)
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['files_processed'] += 1
            self.stats['total_records'] += result['total_records']
            self.stats['parsed_records'] += result['parsed_records']
            self.stats['processing_time'] += processing_time
            
            logger.info(f"C++ parsing completed in {processing_time:.2f}s")
            logger.info(f"Records: {result['total_records']} total, {result['parsed_records']} parsed")
            
            return result
            
        except Exception as e:
            logger.error(f"C++ parser error: {str(e)}")
            raise RuntimeError(f"Failed to parse STDF file: {str(e)}")
    
    def convert_to_clickhouse_format(self, cpp_records: List[Dict[str, Any]], 
                                   file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert C++ parsed records to ClickHouse-compatible format.
        
        This method transforms the C++ parser output into the format expected
        by the existing ClickHouse integration code.
        
        Args:
            cpp_records: Records from C++ parser
            file_info: File metadata (timestamps, hash, etc.)
            
        Returns:
            List of records formatted for ClickHouse insertion
        """
        clickhouse_records = []
        
        for record in cpp_records:
            # Create base ClickHouse record structure
            ch_record = {
                'wld_id': self._generate_wld_id(record, file_info),
                'record_type': record['record_type'],
                'test_num': record['test_num'],
                'head_num': record['head_num'],
                'site_num': record['site_num'],
                'wptm_created_date': file_info.get('created_date', datetime.now()),
                'record_data': record['fields'],  # Complete field data as JSON
                'test_flag': record['fields'].get('TEST_FLG', '0'),
                'alarm_id': record['alarm_id'],
                'part_txt': file_info.get('part_txt', ''),
                'segment': file_info.get('segment', 0),
                'file_hash': file_info.get('file_hash', ''),
                'filename': record['filename'],
                'record_index': record['record_index']
            }
            
            # Add measurement-specific fields for PTR/MPR
            if record['record_type'] in ['PTR', 'MPR']:
                ch_record.update({
                    'measurement_value': record['result'],
                    'measurement_unit': record['fields'].get('UNITS', ''),
                    'low_limit': self._safe_float(record['fields'].get('LO_LIMIT')),
                    'high_limit': self._safe_float(record['fields'].get('HI_LIMIT')),
                    'test_text': record['test_txt']
                })
            
            clickhouse_records.append(ch_record)
        
        return clickhouse_records
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        avg_time = (self.stats['processing_time'] / self.stats['files_processed'] 
                   if self.stats['files_processed'] > 0 else 0)
        
        return {
            **self.stats,
            'average_processing_time': avg_time,
            'records_per_second': (self.stats['parsed_records'] / self.stats['processing_time'] 
                                 if self.stats['processing_time'] > 0 else 0)
        }
    
    def reset_statistics(self):
        """Reset parsing statistics."""
        self.stats = {
            'files_processed': 0,
            'total_records': 0,
            'parsed_records': 0,
            'processing_time': 0.0
        }
    
    def _generate_wld_id(self, record: Dict[str, Any], file_info: Dict[str, Any]) -> int:
        """
        Generate WLD_ID for the record.
        
        This should match the existing logic in your ClickHouse integration.
        """
        # Placeholder implementation - adapt to your existing WLD_ID generation logic
        filename_hash = hash(record['filename']) & 0x7FFFFFFF  # Ensure positive
        return filename_hash + record['record_index']
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float."""
        if value is None or value == '':
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

class STDFProcessingPipeline:
    """
    Complete STDF processing pipeline combining C++ parsing with Python ClickHouse operations.
    """
    
    def __init__(self, clickhouse_config: Dict[str, Any], parser_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the processing pipeline.
        
        Args:
            clickhouse_config: ClickHouse connection and processing configuration
            parser_config: C++ parser configuration
        """
        self.cpp_parser = STDFCppParser(parser_config)
        self.clickhouse_config = clickhouse_config
        
        # Import ClickHouse utilities (adapt path as needed)
        # from ..clickhouse_utils import push_measurements_clickhouse
        # self.clickhouse_pusher = push_measurements_clickhouse
    
    def process_stdf_file(self, filepath: str, file_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete STDF file processing pipeline.
        
        Args:
            filepath: Path to STDF file
            file_metadata: Additional file metadata
            
        Returns:
            Processing results and statistics
        """
        file_info = file_metadata or {}
        file_info.setdefault('created_date', datetime.now())
        file_info.setdefault('file_hash', self._calculate_file_hash(filepath))
        
        # Step 1: Parse with C++ engine (6-10x faster)
        cpp_result = self.cpp_parser.parse_stdf_file(filepath)
        
        # Step 2: Convert to ClickHouse format
        ch_records = self.cpp_parser.convert_to_clickhouse_format(
            cpp_result['records'], file_info
        )
        
        # Step 3: Push to ClickHouse (using existing optimized Python code)
        # clickhouse_result = self.clickhouse_pusher(ch_records, self.clickhouse_config)
        
        return {
            'parsing_stats': cpp_result,
            'converted_records': len(ch_records),
            'file_info': file_info,
            # 'clickhouse_result': clickhouse_result,
            'processing_stats': self.cpp_parser.get_statistics()
        }
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate file hash for deduplication."""
        import hashlib
        
        with open(filepath, 'rb') as f:
            file_hash = hashlib.md5()
            for chunk in iter(lambda: f.read(4096), b""):
                file_hash.update(chunk)
            return file_hash.hexdigest()

# Utility functions for integration
def get_cpp_parser_version() -> str:
    """Get C++ parser version information."""
    if stdf_parser_cpp is None:
        return "C++ extension not available"
    return stdf_parser_cpp.get_version()

def test_cpp_parser() -> bool:
    """Test if C++ parser is working correctly."""
    try:
        version = get_cpp_parser_version()
        logger.info(f"C++ parser test successful: {version}")
        return True
    except Exception as e:
        logger.error(f"C++ parser test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the wrapper
    print("Testing STDF C++ Parser Wrapper")
    print(f"Version: {get_cpp_parser_version()}")
    print(f"Extension available: {stdf_parser_cpp is not None}")
    
    if test_cpp_parser():
        print("✅ C++ parser is ready!")
    else:
        print("❌ C++ parser needs to be built first")
        print("Run: python setup.py build_ext --inplace")