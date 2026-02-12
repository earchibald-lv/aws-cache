"""Tests for cache statistics and monitoring."""
import os
import sys
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


def test_cache_stats_initialization(cache_instance):
    """Cache stats should initialize with zero hits/misses."""
    # FAILING TEST (Red phase)
    stats = cache_instance.get_cache_stats()
    assert stats is not None
    assert stats['hits'] == 0
    assert stats['misses'] == 0
    assert stats['total_calls'] == 0


def test_cache_stats_track_misses(cache_instance, mock_aws_cli):
    """Stats should increment misses on cache miss."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    cache_instance.execute(['sts', 'get-caller-identity'])
    stats = cache_instance.get_cache_stats()
    
    assert stats['misses'] == 1
    assert stats['total_calls'] == 1


def test_cache_stats_track_hits(cache_instance, mock_aws_cli):
    """Stats should increment hits on cache hit."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # First call: cache miss
    cache_instance.execute(['sts', 'get-caller-identity'])
    # Second call: cache hit
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    stats = cache_instance.get_cache_stats()
    assert stats['misses'] == 1
    assert stats['hits'] == 1
    assert stats['total_calls'] == 2
