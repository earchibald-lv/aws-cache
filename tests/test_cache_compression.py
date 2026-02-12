"""Tests for cache compression and size management."""
import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Load the aws-cache executable directly
aws_cache_path = Path(__file__).parent.parent / "aws-cache"
with open(aws_cache_path, 'r') as f:
    code = f.read()

# Execute the code in a namespace to extract AWSCache
namespace = {}
exec(code, namespace)
AWSCache = namespace['AWSCache']


@pytest.fixture
def cache_instance(tmp_path):
    """Create a cache instance with a temporary directory."""
    cache = AWSCache(cache_dir=str(tmp_path), default_ttl=300)
    return cache


@pytest.fixture
def mock_aws_cli(monkeypatch):
    """Mock the subprocess.run call to avoid actual AWS CLI execution."""
    mock = MagicMock(returncode=0, stdout='result', stderr='')
    monkeypatch.setattr('subprocess.run', lambda *args, **kwargs: mock)
    return mock


def test_cache_stores_large_responses(cache_instance, mock_aws_cli):
    """Cache should successfully store large JSON responses."""
    # FAILING TEST (Red phase)
    large_response = json.dumps({'data': ['item' for i in range(100)]})
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout=large_response, stderr='')
    
    cache_instance.execute(['ec2', 'describe-instances'])
    
    # Verify cache file was created
    cache_files = list(cache_instance.cache_dir.glob('*.json'))
    assert len(cache_files) > 0
    
    # Verify cache file contains data
    cache_file = [f for f in cache_files if not f.name.endswith(('operation-types.json', 'aws-service-reference.json'))][0]
    with open(cache_file, 'r') as f:
        cached_data = json.load(f)
        assert 'stdout' in cached_data
        assert large_response in cached_data['stdout']


def test_cache_total_size_calculation(cache_instance, mock_aws_cli):
    """Should be able to calculate total cache size."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute multiple commands to build cache
    cache_instance.execute(['sts', 'get-caller-identity'])
    cache_instance.execute(['ec2', 'describe-instances'])
    cache_instance.execute(['iam', 'list-users'])
    
    # Calculate total cache size
    cache_files = [f for f in cache_instance.cache_dir.glob('*.json') 
                   if not f.name.endswith(('operation-types.json', 'aws-service-reference.json'))]
    total_size = sum(f.stat().st_size for f in cache_files)
    
    # Should have non-zero cache size
    assert total_size > 0
    assert len(cache_files) >= 3


def test_cache_size_display_method(cache_instance, mock_aws_cli):
    """Should have method to get human-readable cache size."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    # Method should exist and return a dict or string with size info
    size_info = getattr(cache_instance, 'get_cache_size', None)
    assert size_info is not None, "get_cache_size method should exist"
