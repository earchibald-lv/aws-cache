"""Tests for graceful degradation when services are unavailable."""
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


def test_cache_disabled_flag_bypasses_cache(cache_instance, mock_aws_cli):
    """When AWS_CACHE_DISABLE=1, should execute directly without cache."""
    # FAILING TEST (Red phase)
    with patch.dict(os.environ, {'AWS_CACHE_DISABLE': '1'}):
        initial_cache_size = len(list(cache_instance.cache_dir.glob('*.json')))
        
        mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
        cache_instance.execute(['sts', 'get-caller-identity'])
        
        final_cache_size = len(list(cache_instance.cache_dir.glob('*.json')))
        
        # Cache should not grow (no new entries created)
        assert final_cache_size == initial_cache_size


def test_no_cache_flag_bypasses_cache_check(cache_instance, mock_aws_cli):
    """--no-cache flag should execute without checking/updating cache."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='v1', stderr='')
    
    # First execution with use_cache=False
    cache_instance.execute(['sts', 'get-caller-identity'], use_cache=False)
    call_count_1 = mock_aws_cli.call_count
    
    # Second execution with use_cache=False
    stdout, _, _ = cache_instance.execute(['sts', 'get-caller-identity'], use_cache=False)
    
    # Should always execute (never cache or retrieve from cache)
    assert mock_aws_cli.call_count == call_count_1 + 1


def test_aws_cli_not_found_returns_error(cache_instance):
    """Should return error message when AWS CLI not found."""
    # FAILING TEST (Red phase)
    with patch('subprocess.run', side_effect=FileNotFoundError("AWS CLI not found")):
        stdout, stderr, returncode = cache_instance.execute(['sts', 'get-caller-identity'])
        
        # Should return specific error
        assert returncode == 127  # Standard "command not found" exit code
        assert 'AWS CLI not found' in stderr


def test_aws_cli_timeout_returns_error(cache_instance):
    """Should return timeout error when AWS CLI takes too long."""
    # FAILING TEST (Red phase)
    import subprocess
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('aws', 300)):
        stdout, stderr, returncode = cache_instance.execute(['sts', 'get-caller-identity'])
        
        # Should return specific error
        assert returncode == 124  # Standard timeout exit code
        assert 'timed out' in stderr
