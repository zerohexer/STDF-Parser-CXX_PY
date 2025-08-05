#!/usr/bin/env python3
"""
Test suite for STDF C++ Parser
"""

import pytest
import os
import sys
import tempfile
import json

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

try:
    from stdf_cpp_wrapper import STDFCppParser, STDFProcessingPipeline, get_cpp_parser_version
    import stdf_parser_cpp
    CPP_EXTENSION_AVAILABLE = True
except ImportError:
    CPP_EXTENSION_AVAILABLE = False

class TestSTDFCppParser:
    """Test cases for STDF C++ Parser"""
    
    def test_cpp_extension_import(self):
        """Test that C++ extension can be imported"""
        if not CPP_EXTENSION_AVAILABLE:
            pytest.skip("C++ extension not built yet")
        
        assert stdf_parser_cpp is not None
        
    def test_get_version(self):
        """Test version information"""
        if not CPP_EXTENSION_AVAILABLE:
            pytest.skip("C++ extension not built yet")
            
        version = get_cpp_parser_version()
        assert isinstance(version, str)
        assert len(version) > 0
        
    def test_parser_initialization(self):
        """Test parser can be initialized"""
        parser = STDFCppParser()
        assert parser is not None
        assert parser.stats['files_processed'] == 0
        
    def test_file_not_found(self):
        """Test handling of non-existent files"""
        if not CPP_EXTENSION_AVAILABLE:
            pytest.skip("C++ extension not built yet")
            
        parser = STDFCppParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_stdf_file("non_existent_file.stdf")
            
    def test_sample_records(self):
        """Test parsing with sample records"""
        if not CPP_EXTENSION_AVAILABLE:
            pytest.skip("C++ extension not built yet")
            
        # Create a temporary dummy file
        with tempfile.NamedTemporaryFile(suffix='.stdf', delete=False) as tmp:
            tmp.write(b"dummy stdf content")
            tmp_path = tmp.name
            
        try:
            parser = STDFCppParser()
            result = parser.parse_stdf_file(tmp_path)
            
            # Verify result structure
            assert 'records' in result
            assert 'total_records' in result
            assert 'parsed_records' in result
            assert isinstance(result['records'], list)
            
            # Check sample records (from our placeholder implementation)
            if len(result['records']) > 0:
                record = result['records'][0]
                assert 'record_type' in record
                assert 'test_num' in record
                assert 'head_num' in record
                assert 'site_num' in record
                assert 'fields' in record
                
        finally:
            os.unlink(tmp_path)
            
    def test_record_conversion(self):
        """Test conversion to ClickHouse format"""
        parser = STDFCppParser()
        
        # Sample C++ record
        cpp_record = {
            'type': 0,  # PTR
            'record_type': 'PTR',
            'test_num': 1000512,
            'head_num': 1,
            'site_num': 1,
            'result': 0.0486745648086071,
            'alarm_id': 'TestAlarm',
            'test_txt': 'TestText',
            'filename': 'test.stdf',
            'record_index': 1,
            'fields': {
                'TEST_NUM': '1000512',
                'HEAD_NUM': '1',
                'SITE_NUM': '1',
                'RESULT': '0.0486745648086071'
            }
        }
        
        file_info = {
            'created_date': '2023-01-01T00:00:00',
            'file_hash': 'test_hash',
            'part_txt': 'TestPart'
        }
        
        ch_records = parser.convert_to_clickhouse_format([cpp_record], file_info)
        
        assert len(ch_records) == 1
        ch_record = ch_records[0]
        
        # Verify ClickHouse record structure
        assert ch_record['record_type'] == 'PTR'
        assert ch_record['test_num'] == 1000512
        assert ch_record['head_num'] == 1
        assert ch_record['site_num'] == 1
        assert ch_record['measurement_value'] == 0.0486745648086071
        assert ch_record['alarm_id'] == 'TestAlarm'
        assert ch_record['file_hash'] == 'test_hash'
        
    def test_statistics(self):
        """Test statistics collection"""
        parser = STDFCppParser()
        
        # Initial stats
        stats = parser.get_statistics()
        assert stats['files_processed'] == 0
        assert stats['total_records'] == 0
        assert stats['parsed_records'] == 0
        
        # Reset stats
        parser.reset_statistics()
        stats = parser.get_statistics()
        assert stats['files_processed'] == 0

class TestSTDFProcessingPipeline:
    """Test cases for complete processing pipeline"""
    
    def test_pipeline_initialization(self):
        """Test pipeline can be initialized"""
        config = {'host': 'localhost', 'port': 9000}
        pipeline = STDFProcessingPipeline(config)
        
        assert pipeline is not None
        assert pipeline.clickhouse_config == config
        assert pipeline.cpp_parser is not None

if __name__ == "__main__":
    # Run basic tests
    print("Running STDF C++ Parser Tests")
    print("=" * 50)
    
    print(f"C++ Extension Available: {CPP_EXTENSION_AVAILABLE}")
    
    if CPP_EXTENSION_AVAILABLE:
        print(f"Version: {get_cpp_parser_version()}")
    else:
        print("❌ C++ extension not built. Run 'python setup.py build_ext --inplace'")
        
    # Run pytest
    pytest.main([__file__, "-v"])