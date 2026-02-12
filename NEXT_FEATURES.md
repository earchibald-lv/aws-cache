# AWS-Cache: Next Features for TDD Development

## Overview
This document identifies high-value features for aws-cache development using strict Test-Driven Development (TDD) principles. Each feature includes Red Phase skeleton tests—failing tests that describe the desired behavior.

---

## Feature 1: Cache Statistics and Monitoring

### Purpose
Track cache hit/miss rates and provide insights into cache effectiveness. Enable users to understand which operations benefit most from caching.

### Red Phase Test Skeleton

```python
# tests/test_cache_statistics.py
"""Tests for cache statistics and monitoring."""

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

def test_cache_stats_by_operation(cache_instance, mock_aws_cli):
    """Stats should track hits/misses by operation type."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute different operations
    cache_instance.execute(['sts', 'get-caller-identity'])
    cache_instance.execute(['ec2', 'describe-instances'])
    cache_instance.execute(['sts', 'get-caller-identity'])  # Cache hit
    
    stats = cache_instance.get_cache_stats()
    assert 'sts:GetCallerIdentity' in stats['by_operation']
    assert stats['by_operation']['sts:GetCallerIdentity']['hits'] == 1
    assert stats['by_operation']['sts:GetCallerIdentity']['misses'] == 1

def test_cache_stats_display_command(cache_instance):
    """--cache-stats flag should display statistics."""
    # FAILING TEST (Red phase)
    # Usage: aws-cache --cache-stats
    # Should print formatted cache statistics to stdout
    pass
```

### Implementation Notes
- Store stats in memory during execution, optionally persist to disk
- Track hits/misses per operation (service:Action format)
- Include metrics: hit rate %, bytes saved, time saved estimates
- Reset stats with `--cache-stats-reset` flag

---

## Feature 2: Cache Invalidation by Pattern

### Purpose
Allow users to selectively invalidate cache entries by pattern (e.g., all S3 operations, all operations for a specific region).

### Red Phase Test Skeleton

```python
# tests/test_cache_invalidation.py
"""Tests for cache invalidation by pattern."""

def test_invalidate_cache_by_service(cache_instance, mock_aws_cli):
    """Should invalidate all cache entries for a service."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Populate cache with multiple operations
    cache_instance.execute(['ec2', 'describe-instances'])
    cache_instance.execute(['ec2', 'describe-volumes'])
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    # Invalidate all EC2 cache
    cache_instance.invalidate_cache_by_pattern(service='ec2')
    
    # STS should still be cached (if called again)
    # EC2 should be re-executed (not cached)
    pass

def test_invalidate_cache_by_region(cache_instance, mock_aws_cli):
    """Should invalidate all cache entries for a specific region."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Populate cache for different regions
    with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-east-1'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    with patch.dict('os.environ', {'AWS_DEFAULT_REGION': 'us-west-2'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    # Invalidate us-east-1 cache
    cache_instance.invalidate_cache_by_pattern(region='us-east-1')
    
    # us-west-2 should still be cached
    # us-east-1 should be re-executed (not cached)
    pass

def test_cache_invalidation_cli_flag(cache_instance):
    """--cache-invalidate flag should accept patterns."""
    # FAILING TEST (Red phase)
    # Usage examples:
    # aws-cache --cache-invalidate "ec2:*"
    # aws-cache --cache-invalidate "service:ec2"
    # aws-cache --cache-invalidate "region:us-west-2"
    pass

def test_invalidate_cache_by_age(cache_instance, mock_aws_cli):
    """Should invalidate cache entries older than specified age."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute command to populate cache
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    # Mock time to simulate aging
    with patch('time.time') as mock_time:
        # Advance time by 600 seconds (10 minutes)
        mock_time.return_value = time.time() + 600
        
        # Invalidate cache older than 5 minutes
        cache_instance.invalidate_cache_by_pattern(max_age_seconds=300)
    
    # Cache should be invalidated (re-executed on next call)
    pass
```

### Implementation Notes
- Support regex patterns for service/operation names
- Allow combining filters (service AND region)
- Provide feedback on how many entries were invalidated
- Add `--cache-invalidate-pattern` CLI flag

---

## Feature 3: Graceful Degradation and Fallback Modes

### Purpose
When AWS Service Reference API is unavailable, fall back gracefully to heuristic-based classification. Maintain functionality even during network issues.

### Red Phase Test Skeleton

```python
# tests/test_degradation.py
"""Tests for graceful degradation when services are unavailable."""

def test_fallback_to_heuristics_when_api_unavailable(cache_instance, mock_urllib):
    """Should fall back to IAM heuristics when AWS Service Reference API fails."""
    # FAILING TEST (Red phase)
    mock_urllib.side_effect = ConnectionError("Cannot reach AWS Service Reference API")
    
    # Should still classify operation using IAM naming heuristics
    classification = cache_instance._determine_operation_type(['ec2', 'describe-instances'])
    assert classification == 'read'
    
    # Should print warning (not fail)
    # Verification: check stderr for fallback message

def test_cache_disabled_flag_falls_back_to_direct_execution(cache_instance, mock_aws_cli):
    """When AWS_CACHE_DISABLE=1, should execute directly without cache."""
    # FAILING TEST (Red phase)
    with patch.dict('os.environ', {'AWS_CACHE_DISABLE': '1'}):
        initial_cache_size = len(list(cache_instance.cache_dir.glob('*.json')))
        
        mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
        cache_instance.execute(['sts', 'get-caller-identity'])
        
        final_cache_size = len(list(cache_instance.cache_dir.glob('*.json')))
        
        # Cache should not grow
        assert final_cache_size == initial_cache_size

def test_no_cache_flag_bypasses_cache_check(cache_instance, mock_aws_cli):
    """--no-cache flag should execute without checking/updating cache."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='v1', stderr='')
    
    # First execution with --no-cache
    cache_instance.execute(['sts', 'get-caller-identity'], use_cache=False)
    call_count_1 = mock_aws_cli.call_count
    
    # Second execution with --no-cache
    stdout, _, _ = cache_instance.execute(['sts', 'get-caller-identity'], use_cache=False)
    
    # Should always execute (never cache or retrieve from cache)
    assert mock_aws_cli.call_count == call_count_1 + 1

def test_service_reference_api_timeout_uses_fallback(cache_instance, mock_urllib):
    """Should use fallback if AWS Service Reference API times out."""
    # FAILING TEST (Red phase)
    mock_urllib.side_effect = TimeoutError("AWS Service Reference API timed out")
    
    # Should still classify operation using fallback
    classification = cache_instance._determine_operation_type(['iam', 'list-users'])
    assert classification == 'read'
```

### Implementation Notes
- Emit warnings when falling back to heuristics (not errors)
- Respect `AWS_CACHE_DISABLE` environment variable
- Support `--no-cache` and `--cache-disable` CLI flags
- Graceful timeout handling for external API calls (5-10 second timeout)

---

## Feature 4: Cache Compression and Size Management

### Purpose
Reduce disk space used by cache, especially for large API responses. Allow users to compress cache and set size limits.

### Red Phase Test Skeleton

```python
# tests/test_cache_compression.py
"""Tests for cache compression and size management."""

def test_cache_compression_gzip(cache_instance, mock_aws_cli):
    """Cache should compress large responses using gzip."""
    # FAILING TEST (Red phase)
    large_response = json.dumps({'data': ['item' for i in range(1000)]})
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout=large_response, stderr='')
    
    cache_instance.execute(['ec2', 'describe-instances'])
    
    # Cache file should be compressed (smaller than original)
    cache_file = list(cache_instance.cache_dir.glob('*.json'))[0]
    original_size = len(large_response.encode())
    cache_size = cache_file.stat().st_size
    
    assert cache_size < original_size

def test_cache_max_size_limit(cache_instance, mock_aws_cli):
    """Cache should not exceed maximum size limit."""
    # FAILING TEST (Red phase)
    # Set max cache size to 1 MB
    cache_instance.cache_max_size = 1024 * 1024
    
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute many commands to fill cache beyond limit
    for i in range(1000):
        cache_instance.execute(['ec2', 'describe-instances', '--instance-id', f'i-{i}'])
    
    # Total cache size should not exceed limit
    total_size = sum(f.stat().st_size for f in cache_instance.cache_dir.glob('*.json'))
    assert total_size <= cache_instance.cache_max_size

def test_cache_size_display_command(cache_instance):
    """--cache-size command should display cache disk usage."""
    # FAILING TEST (Red phase)
    # Usage: aws-cache --cache-size
    # Should print human-readable cache size (e.g., "2.3 MB")
    pass

def test_cache_cleanup_by_lru(cache_instance, mock_aws_cli):
    """Should evict least-recently-used entries when size limit exceeded."""
    # FAILING TEST (Red phase)
    cache_instance.cache_max_size = 100  # Very small limit
    
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute first command
    cache_instance.execute(['sts', 'get-caller-identity'])
    cache_file_1 = list(cache_instance.cache_dir.glob('*.json'))[0]
    
    # Sleep/advance time
    # Execute many more commands to trigger cleanup
    # Verify first cache file was evicted
    pass
```

### Implementation Notes
- Use gzip compression for responses > 1 KB
- Store uncompressed responses in memory for speed
- LRU (Least Recently Used) eviction policy
- Configuration: `--cache-max-size`, `AWS_CACHE_MAX_SIZE`
- Display cache stats: size, compression ratio, eviction count

---

## Feature 5: Cache Versioning and Format Migrations

### Purpose
Support cache format evolution without breaking existing caches. Version the cache format so changes can be handled gracefully.

### Red Phase Test Skeleton

```python
# tests/test_cache_versioning.py
"""Tests for cache versioning and format migrations."""

def test_cache_format_version_stored(cache_instance, mock_aws_cli):
    """Cache should store format version for future compatibility."""
    # FAILING TEST (Red phase)
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='{}', stderr='', returncode=0)
    
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    # Read cache file
    cache_files = list(cache_instance.cache_dir.glob('*.json'))
    with open(cache_files[0], 'r') as f:
        cache_data = json.load(f)
    
    # Should have version field
    assert 'format_version' in cache_data
    assert cache_data['format_version'] == cache_instance.CACHE_FORMAT_VERSION

def test_legacy_cache_format_still_readable(cache_instance):
    """Should read legacy cache format from previous versions."""
    # FAILING TEST (Red phase)
    # Create cache file in legacy format (without version field)
    legacy_cache_data = {
        'stdout': '{}',
        'stderr': '',
        'returncode': 0,
        'command': ['sts', 'get-caller-identity'],
        'timestamp': time.time()
    }
    
    cache_key = cache_instance._get_cache_key(['sts', 'get-caller-identity'])
    cache_file = cache_instance._get_cache_file(cache_key)
    
    with open(cache_file, 'w') as f:
        json.dump(legacy_cache_data, f)
    
    # Should be able to read legacy format
    stdout, stderr, rc = cache_instance._read_cache(cache_file)
    assert stdout == '{}'
    assert stderr == ''
    assert rc == 0

def test_cache_format_migration_on_upgrade(cache_instance):
    """Should migrate cache format when upgrading to new version."""
    # FAILING TEST (Red phase)
    # Populate cache with legacy format
    # Run migration command: aws-cache --migrate-cache
    # Verify all cache entries are updated to new format
    pass

def test_incompatible_cache_format_invalidated(cache_instance):
    """Should invalidate cache if format version is incompatible."""
    # FAILING TEST (Red phase)
    # Create cache with future/incompatible format version
    future_cache_data = {
        'format_version': 999,  # Future version
        'stdout': '{}',
        'stderr': '',
        'returncode': 0,
        'command': ['sts', 'get-caller-identity'],
        'timestamp': time.time()
    }
    
    cache_key = cache_instance._get_cache_key(['sts', 'get-caller-identity'])
    cache_file = cache_instance._get_cache_file(cache_key)
    
    with open(cache_file, 'w') as f:
        json.dump(future_cache_data, f)
    
    # Should not use incompatible cache
    stdout, stderr, rc = cache_instance._read_cache(cache_file)
    # Should return None (cache invalid)
    assert stdout is None
```

### Implementation Notes
- Add `CACHE_FORMAT_VERSION = 1` constant
- Store version in every cache JSON file
- Implement migration function for format upgrades
- Reject cache files with incompatible versions
- Document cache format schema in README

---

## Development Priority Matrix

| Feature | Effort | Value | Risk | Priority |
|---------|--------|-------|------|----------|
| 1. Cache Statistics | Low | High | Low | **HIGH** |
| 2. Cache Invalidation | Medium | High | Low | **HIGH** |
| 3. Graceful Degradation | Medium | Medium | High | **MEDIUM** |
| 4. Cache Compression | Medium | Medium | Low | **MEDIUM** |
| 5. Cache Versioning | Low | Medium | Low | **MEDIUM** |

---

## Next Steps

1. **Pick Feature 1 (Cache Statistics)** as first TDD implementation:
   - Write all RED phase tests from skeleton above
   - Run tests (all should FAIL)
   - Implement minimal code (GREEN phase)
   - Refactor for clarity (REFACTOR phase)
   - Submit PR with test evidence

2. **Create feature branch**:
   ```bash
   git checkout -b feature/cache-statistics
   ```

3. **Commit atomically** (one phase per commit):
   ```bash
   # Commit 1: Add failing tests (RED phase)
   git add tests/test_cache_statistics.py
   git commit -m "Add tests for cache statistics (RED phase)"
   
   # Commit 2: Implement statistics tracking (GREEN phase)
   git add aws-cache
   git commit -m "Implement cache statistics tracking (GREEN phase)"
   
   # Commit 3: Refactor for clarity (REFACTOR phase)
   git add aws-cache
   git commit -m "Refactor cache statistics calculation (REFACTOR phase)"
   ```

4. **Verify coverage**:
   ```bash
   pytest --cov=aws-cache tests/test_cache_statistics.py
   # Target: >= 95% coverage for statistics module
   ```

5. **Open PR with description**:
   - Link issue if applicable
   - Include before/after coverage report
   - Demonstrate usage: `aws-cache --cache-stats`
   - Show test results: `pytest tests/test_cache_statistics.py -v`

---

## Testing Best Practices (from TESTING_STRATEGY.md)

✓ Use fixtures for isolation (`cache_instance`, `mock_aws_cli`, `temp_cache_dir`)
✓ Mock all external calls (subprocess, urllib, os.environ)
✓ Never check/modify actual AWS state
✓ Test one behavior per test function
✓ Use descriptive test names: `test_<scenario>_<expected_result>`
✓ Always verify coverage: `pytest --cov` before PR
