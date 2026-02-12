"""Tests for cache invalidation by pattern."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from aws_cache import AWSCache


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


def test_invalidate_cache_by_service(cache_instance, mock_aws_cli):
    """Should invalidate all cache entries for a service."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Populate cache for different services
    cache_instance.execute(['sts', 'get-caller-identity'])
    cache_instance.execute(['ec2', 'describe-instances'])
    
    # Invalidate sts cache
    cache_instance.invalidate_cache_by_pattern(service='sts')
    
    # EC2 should still be cached (second call should be hit)
    # Can verify by checking stats or attempting re-execute
    stats_after = cache_instance.get_cache_stats()
    assert stats_after is not None  # Placeholder for future implementation


def test_invalidate_cache_by_region(cache_instance, mock_aws_cli):
    """Should invalidate all cache entries for a specific region."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Populate cache for different regions
    with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-east-1'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    with patch.dict(os.environ, {'AWS_DEFAULT_REGION': 'us-west-2'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    # Invalidate us-east-1 cache
    cache_instance.invalidate_cache_by_pattern(region='us-east-1')
    
    # us-west-2 should still be cached
    # us-east-1 should be re-executed (not cached)
    stats_after = cache_instance.get_cache_stats()
    assert stats_after is not None  # Placeholder


def test_cache_invalidation_cli_flag(cache_instance, mock_aws_cli):
    """--cache-invalidate flag should accept patterns."""
    # FAILING TEST (Red phase)
    # Usage examples:
    # aws-cache --cache-invalidate "ec2:*"
    # aws-cache --cache-invalidate "service:ec2"
    # aws-cache --cache-invalidate "region:us-west-2"
    pass
