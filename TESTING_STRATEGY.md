# AWS-Cache Testing Strategy Guide

## Overview
This guide provides a comprehensive testing strategy for aws-cache, enabling Test-Driven Development (TDD) with emphasis on safety, isolation, and maintainability.

---

## 1. Test Structure and Organization

### Naming Conventions
- **Test files**: `test_<feature>.py` (e.g., `test_cache_context.py`, `test_operation_classification.py`)
- **Test classes**: `Test<Feature>` (e.g., `TestCacheContext`, `TestOperationClassification`)
- **Test functions**: `test_<scenario>` (e.g., `test_extract_profile_from_args`, `test_read_operation_caches`)
- **Parametrized tests**: Use `@pytest.mark.parametrize` for multiple related scenarios

### File Organization
```
tests/
├── __init__.py
├── test_cache_context.py       # Profile, region, context isolation
├── test_argument_normalization.py  # Flag sorting and arg consistency
├── test_cache_operations.py    # Cache read/write/validity
├── test_operation_classification.py  # Read/write determination
├── test_aws_cli_execution.py   # Subprocess mocking and execution
├── test_authoritative_api.py   # AWS Service Reference API mocking
├── test_cli_interface.py       # --profile, --cache-ttl, flags
├── test_edge_cases.py          # Error handling, edge cases
├── conftest.py                 # Shared fixtures (see section 2)
└── fixtures/
    ├── aws_responses.py        # Canned AWS CLI responses
    ├── service_definitions.py  # Mock AWS Service Reference data
    └── cache_states.py         # Pre-built cache state fixtures
```

---

## 2. Test Fixtures and Mocking

### Shared Fixtures (conftest.py)

```python
# conftest.py
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Load aws-cache for testing
aws_cache_path = Path(__file__).parent.parent / "aws-cache"
namespace = {}
with open(aws_cache_path, 'r') as f:
    exec(f.read(), namespace)
AWSCache = namespace['AWSCache']

@pytest.fixture
def temp_cache_dir():
    """Create isolated temporary cache directory for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def cache_instance(temp_cache_dir):
    """Provide a clean AWSCache instance with temporary directory."""
    return AWSCache(cache_dir=temp_cache_dir, default_ttl=300)

@pytest.fixture
def mock_aws_cli():
    """Mock the subprocess.run call to AWS CLI."""
    with patch('subprocess.run') as mock_run:
        # Default: return success with empty output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )
        yield mock_run

@pytest.fixture
def mock_urllib():
    """Mock urllib for AWS Service Reference API calls."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Not mocked by test")
        yield mock_urlopen

@pytest.fixture
def isolated_env():
    """Provide isolated environment with specific AWS variables."""
    original_env = {}
    aws_keys = ['AWS_PROFILE', 'AWS_DEFAULT_REGION', 'AWS_CACHE_DIR', 'AWS_CACHE_TTL', 'AWS_CACHE_DISABLE']
    
    for key in aws_keys:
        original_env[key] = os.environ.pop(key, None)
    
    yield {}
    
    # Restore original environment
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]
```

### AWS CLI Response Fixtures

```python
# fixtures/aws_responses.py
import json

DESCRIBE_INSTANCES_SUCCESS = {
    'returncode': 0,
    'stdout': json.dumps({
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-1234567890abcdef0',
                'InstanceType': 't2.micro',
                'State': {'Name': 'running'}
            }]
        }]
    }),
    'stderr': ''
}

LIST_USERS_SUCCESS = {
    'returncode': 0,
    'stdout': json.dumps({
        'Users': [
            {'UserName': 'alice', 'UserId': 'AIDACKCEVSQ6C2EXAMPLE'},
            {'UserName': 'bob', 'UserId': 'AIDACKCEVSQ6C2EXAMPLE2'}
        ]
    }),
    'stderr': ''
}

GET_CALLER_IDENTITY_SUCCESS = {
    'returncode': 0,
    'stdout': json.dumps({
        'UserId': 'AIDAI23HXD2O7TZYJVHYE',
        'Account': '123456789012',
        'Arn': 'arn:aws:iam::123456789012:user/Developer'
    }),
    'stderr': ''
}

AWS_CLI_NOT_FOUND = {
    'returncode': 127,
    'stdout': '',
    'stderr': 'aws: command not found'
}

AWS_CALL_ERROR = {
    'returncode': 1,
    'stdout': '',
    'stderr': 'An error occurred (UnauthorizedOperation) when calling the DescribeInstances operation'
}

OPERATION_TIMEOUT = {
    'returncode': 124,
    'stdout': '',
    'stderr': 'AWS CLI command timed out'
}
```

### AWS Service Reference Fixtures

```python
# fixtures/service_definitions.py

EC2_SERVICE_DEFINITION = {
    'Actions': [
        {
            'Name': 'DescribeInstances',
            'Annotations': {'Properties': {'IsWrite': False}}
        },
        {
            'Name': 'RunInstances',
            'Annotations': {'Properties': {'IsWrite': True}}
        },
        {
            'Name': 'TerminateInstances',
            'Annotations': {'Properties': {'IsWrite': True}}
        }
    ]
}

IAM_SERVICE_DEFINITION = {
    'Actions': [
        {
            'Name': 'GetUser',
            'Annotations': {'Properties': {'IsWrite': False}}
        },
        {
            'Name': 'CreateUser',
            'Annotations': {'Properties': {'IsWrite': True}}
        },
        {
            'Name': 'ListUsers',
            'Annotations': {'Properties': {'IsWrite': False}}
        }
    ]
}

S3_SERVICE_DEFINITION = {
    'Actions': [
        {
            'Name': 'ListBucket',
            'Annotations': {'Properties': {'IsWrite': False}}
        },
        {
            'Name': 'PutObject',
            'Annotations': {'Properties': {'IsWrite': True}}
        },
        {
            'Name': 'DeleteObject',
            'Annotations': {'Properties': {'IsWrite': True}}
        }
    ]
}
```

---

## 3. Mocking Strategies

### Strategy A: Mock subprocess.run for AWS CLI

Use when: Testing cache behavior without requiring actual AWS credentials.

```python
def test_read_operation_caches_successfully(cache_instance, mock_aws_cli):
    """Read operations should write results to cache."""
    mock_aws_cli.return_value = MagicMock(
        returncode=0,
        stdout='{"Instances": []}',
        stderr=''
    )
    
    # First call executes AWS CLI
    stdout1, stderr1, rc1 = cache_instance.execute(['ec2', 'describe-instances'])
    assert mock_aws_cli.call_count == 1
    
    # Second call should hit cache (mock not called again)
    stdout2, stderr2, rc2 = cache_instance.execute(['ec2', 'describe-instances'])
    assert mock_aws_cli.call_count == 1  # Still 1, not 2
    assert stdout1 == stdout2
```

### Strategy B: Mock urllib for AWS Service Reference API

Use when: Testing authoritative classification without network calls.

```python
def test_authoritative_classification_ec2_describe(cache_instance, mock_urllib):
    """Authoritative API should correctly classify ec2:DescribeInstances as read."""
    from unittest.mock import Mock
    
    # Mock the HTTP response from AWS Service Reference API
    mock_response = Mock()
    mock_response.__enter__.return_value.read.return_value = json.dumps({
        'Actions': [
            {
                'Name': 'DescribeInstances',
                'Annotations': {'Properties': {'IsWrite': False}}
            }
        ]
    }).encode()
    
    mock_urllib.return_value = mock_response
    
    classification = cache_instance._get_authoritative_classification(['ec2', 'describe-instances'])
    assert classification == 'read'
```

### Strategy C: Mock os.environ for Environment Variables

Use when: Testing profile/region precedence without polluting environment.

```python
def test_profile_precedence_with_mock_env(cache_instance):
    """CLI --profile should take precedence over AWS_PROFILE env."""
    with patch.dict('os.environ', {'AWS_PROFILE': 'env-profile'}):
        context = cache_instance._get_aws_context(['ec2', 'describe-instances', '--profile', 'cli-profile'])
        assert context['profile'] == 'cli-profile'
```

### Strategy D: Mock subprocess for subprocess calls within aws-cache

Use when: Testing cache key generation, operation type determination without side effects.

```python
def test_cache_isolation_by_profile(cache_instance, mock_aws_cli):
    """Cache should isolate by profile - different profiles get different cache hits."""
    mock_aws_cli.return_value = MagicMock(returncode=0, stdout='result', stderr='')
    
    # Execute with profile 'dev'
    with patch.dict('os.environ', {'AWS_PROFILE': 'dev'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    # Execute with profile 'prod'
    with patch.dict('os.environ', {'AWS_PROFILE': 'prod'}):
        cache_instance.execute(['ec2', 'describe-instances'])
    
    # Both should call AWS CLI (not hit cache) because profiles differ
    assert mock_aws_cli.call_count == 2
```

---

## 4. Test Independence and Isolation

### Golden Rules
1. **No test should depend on another test's state**
   - Use fixtures (temp_cache_dir, isolated_env) to isolate each test
   - Never share cache directories between tests

2. **No test should modify global state**
   - Use `patch.dict('os.environ', ...)` for environment variables
   - Use mocks for all external calls (AWS CLI, HTTP, filesystem)

3. **No test should require actual AWS credentials**
   - Mock all AWS CLI calls via subprocess.run
   - Mock all AWS Service Reference API calls via urllib

4. **No test should have temporal dependencies**
   - Mock time.time() if testing TTL expiration
   - Don't rely on actual sleep() calls; use mocks

### Anti-patterns to Avoid
```python
# ❌ BAD: Tests share global cache directory
CACHE_DIR = "/tmp/shared-cache"  # Never do this

# ❌ BAD: Test modifies os.environ without restoration
def test_something():
    os.environ['AWS_PROFILE'] = 'test'
    # ... test code ...
    # Forgot to restore!

# ❌ BAD: Test creates actual AWS API calls
def test_caching():
    cache.execute(['ec2', 'describe-instances'])  # Real API call!

# ❌ BAD: Tests depend on execution order
def test_a():
    cache.execute(...)  # Populates cache

def test_b():
    cache.execute(...)  # Assumes cache from test_a exists
```

---

## 5. Coverage Expectations

### Target Coverage
- **Overall**: ≥ 85% code coverage
- **Critical paths**: ≥ 95% (cache operations, operation type classification, context isolation)
- **Edge cases**: 100% (error handling, invalid inputs)

### Coverage Commands
```bash
# Run tests with coverage report
pytest --cov=aws-cache --cov-report=term-missing tests/

# Generate HTML coverage report
pytest --cov=aws-cache --cov-report=html tests/
open htmlcov/index.html

# Check coverage by file
pytest --cov=aws-cache --cov-report=term-missing:skip-covered tests/
```

### What to Measure
- Line coverage: Ensure all code paths executed
- Branch coverage: Test both if/else branches
- Function coverage: Every public method tested
- Exception coverage: Error paths tested

---

## 6. Test Execution and Best Practices

### Run Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cache_operations.py

# Run specific test
pytest tests/test_cache_operations.py::test_cache_hit_returns_cached_output

# Run with verbose output
pytest -v

# Run with short traceback
pytest --tb=short

# Run and stop on first failure
pytest -x

# Run failed tests only
pytest --lf

# Run with markers
pytest -m "not integration"
```

### Test Markers
```python
# Mark slow tests to skip during rapid iteration
@pytest.mark.slow
def test_large_response_caching():
    pass

# Mark integration tests (require AWS credentials)
@pytest.mark.integration
def test_real_aws_call():
    pass

# Mark fixtures or features under development
@pytest.mark.wip  # Work in progress
def test_new_feature():
    pass
```

---

## 7. Parametrized Testing

Use parametrized tests to cover multiple scenarios concisely:

```python
@pytest.mark.parametrize('operation,expected_type', [
    ('describe-instances', 'read'),
    ('list-users', 'read'),
    ('get-user', 'read'),
    ('create-user', 'write'),
    ('delete-user', 'write'),
    ('update-user', 'write'),
    ('run-instances', 'write'),
    ('terminate-instances', 'write'),
])
def test_operation_classification(cache_instance, operation, expected_type):
    """Test operation type classification for various operations."""
    result = cache_instance._classify_iam_action_name(f'iam:{operation}')
    assert result == expected_type
```

---

## 8. Temporal and Async Testing

### Testing TTL Expiration
```python
def test_cache_expires_after_ttl(cache_instance, mock_aws_cli):
    """Cache should expire when TTL is exceeded."""
    # Mock time.time() to control the clock
    with patch('time.time') as mock_time:
        mock_time.return_value = 1000.0
        mock_aws_cli.return_value = MagicMock(returncode=0, stdout='v1', stderr='')
        
        # First call caches result
        cache_instance.execute(['sts', 'get-caller-identity'], ttl=100)
        
        # Advance time by 50 seconds (within TTL)
        mock_time.return_value = 1050.0
        mock_aws_cli.return_value = MagicMock(returncode=0, stdout='v1', stderr='')
        cache_instance.execute(['sts', 'get-caller-identity'], ttl=100)
        assert mock_aws_cli.call_count == 1  # Hit cache
        
        # Advance time by 60 seconds (past TTL)
        mock_time.return_value = 1110.0
        mock_aws_cli.return_value = MagicMock(returncode=0, stdout='v2', stderr='')
        cache_instance.execute(['sts', 'get-caller-identity'], ttl=100)
        assert mock_aws_cli.call_count == 2  # Cache expired, new call
```

---

## 9. Error Handling and Exception Testing

### Test Exception Handling
```python
def test_aws_cli_not_found_error(cache_instance, mock_aws_cli):
    """Should handle AWS CLI not found gracefully."""
    mock_aws_cli.side_effect = FileNotFoundError()
    
    stdout, stderr, rc = cache_instance.execute(['sts', 'get-caller-identity'])
    assert rc == 127
    assert 'AWS CLI not found' in stderr

def test_aws_cli_timeout(cache_instance, mock_aws_cli):
    """Should handle AWS CLI timeout gracefully."""
    mock_aws_cli.side_effect = subprocess.TimeoutExpired('aws', 300)
    
    stdout, stderr, rc = cache_instance.execute(['sts', 'get-caller-identity'])
    assert rc == 124
    assert 'timed out' in stderr
```

---

## 10. Red Phase Examples (Feature Skeleton Tests)

When starting a new feature with TDD, write tests FIRST (Red phase):

### Feature 1: Cache Expiry Notifications
```python
# tests/test_cache_notifications.py (RED PHASE)

def test_expiry_warning_message(cache_instance):
    """Cache expiry should emit warning before TTL expires."""
    # This test will FAIL initially (Red phase)
    warning = cache_instance._get_expiry_warning(remaining_seconds=30)
    assert warning is not None
    assert '30 seconds' in warning
```

### Feature 2: Cache Statistics
```python
# tests/test_cache_stats.py (RED PHASE)

def test_cache_stats_tracks_hits_and_misses(cache_instance, mock_aws_cli):
    """Cache stats should track cache hits and misses."""
    # This test will FAIL initially (Red phase)
    stats = cache_instance.get_cache_stats()
    assert stats['hits'] == 0
    assert stats['misses'] == 0
    
    # Execute command
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    stats = cache_instance.get_cache_stats()
    assert stats['misses'] == 1
    
    # Execute same command again
    cache_instance.execute(['sts', 'get-caller-identity'])
    
    stats = cache_instance.get_cache_stats()
    assert stats['hits'] == 1
```

### Feature 3: Graceful Degradation
```python
# tests/test_degradation.py (RED PHASE)

def test_cache_disabled_falls_back_to_direct_execution(cache_instance, mock_aws_cli):
    """When cache is disabled, should execute directly without caching."""
    # This test will FAIL initially (Red phase)
    with patch.dict('os.environ', {'AWS_CACHE_DISABLE': '1'}):
        cache_instance.execute(['sts', 'get-caller-identity'])
        
        # Should execute AWS CLI without checking cache
        assert mock_aws_cli.called
```

---

## 11. When to Mock vs. Integrate

### Always Mock
- AWS CLI subprocess calls (`subprocess.run`)
- AWS Service Reference API calls (`urllib.request.urlopen`)
- Environment variables (`os.environ`)
- File I/O for cache operations (in unit tests)
- Time (`time.time()` for TTL testing)

### Never Mock (Integration Tests)
- Core caching logic (cache key generation, TTL comparison)
- Argument normalization
- Operation type classification (local heuristics)
- Cache file read/write to temp directories

### Integration Test Pattern
```python
@pytest.mark.integration
def test_end_to_end_caching_workflow(cache_instance, mock_aws_cli):
    """Integration test for complete caching workflow."""
    mock_aws_cli.return_value = MagicMock(
        returncode=0,
        stdout='{"data": "test"}',
        stderr=''
    )
    
    # First execution
    stdout1, _, _ = cache_instance.execute(['ec2', 'describe-instances'])
    
    # Second execution (should hit cache)
    stdout2, _, _ = cache_instance.execute(['ec2', 'describe-instances'])
    
    # Verify cache was used
    assert stdout1 == stdout2
    assert mock_aws_cli.call_count == 1
```

---

## 12. Common Testing Patterns

### Pattern 1: Test Fixture Cleanup
```python
@pytest.fixture
def service_reference_cache(temp_cache_dir):
    """Create pre-populated service reference cache."""
    cache_file = temp_cache_dir / "aws-service-reference.json"
    cache_file.write_text(json.dumps({
        'ec2:DescribeInstances': 'read',
        'ec2:RunInstances': 'write',
    }))
    return cache_file
```

### Pattern 2: Parametrized Fixtures
```python
@pytest.fixture(params=['default', 'prod', 'staging'])
def aws_profile(request):
    """Parametrized fixture for different AWS profiles."""
    return request.param

def test_cache_isolation_by_profile(cache_instance, mock_aws_cli, aws_profile):
    """Cache isolates correctly by profile."""
    with patch.dict('os.environ', {'AWS_PROFILE': aws_profile}):
        cache_instance.execute(['sts', 'get-caller-identity'])
```

### Pattern 3: Capturing stderr/stdout
```python
def test_warning_on_unknown_operation(cache_instance, capsys):
    """Should warn when operation type is unknown."""
    cache_instance._classify_iam_action_name('unknown:operation')
    
    captured = capsys.readouterr()
    assert 'Unknown operation type' in captured.err
```

---

## Summary

This testing strategy enables:
- ✅ Complete isolation between tests (no shared state)
- ✅ Fast, predictable test execution (no external dependencies)
- ✅ Comprehensive coverage (85%+ target)
- ✅ Clear Red-Green-Refactor cycle
- ✅ Easy addition of new features (skeleton tests first)
- ✅ Regression prevention through continuous testing

Follow these patterns, and aws-cache will remain reliable, maintainable, and safe.
