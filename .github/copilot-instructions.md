# AWS-Cache Development Guidelines

## Project Overview
A lightweight Python3 wrapper that adds intelligent caching to AWS CLI commands. Reduces API latency 10-100x for safe read operations using authoritative AWS Service Reference classifications. Zero external dependencies—pure stdlib only.

## Code Style
- **Python 3.x** with `#!/usr/bin/env python3` shebang (standalone executable)
- **No external dependencies**—only stdlib: `json`, `os`, `sys`, `hashlib`, `subprocess`, `time`, `pathlib`, `argparse`, `urllib` (optional)
- **Monolithic design**: Single [aws-cache](aws-cache) file; keep it self-contained for portability
- **Docstrings**: PEP 257 format with clear examples for public methods
- **Error handling**: Fail gracefully with stderr messages; never break the AWS CLI execution path

## Architecture

### Core Flow
1. **Argument Parsing** → Extract `--profile`, `--cache-ttl`, etc.
2. **AWS Context** → Build cache key from normalized args + profile/region (isolation by account)
3. **Classification** → Determine read/write via: AWS Service Reference API (authoritative) → IAM naming heuristics → warn unknown
4. **Cache Check** → Hit if read operation, valid TTL, matching context
5. **Execution** → Run `aws` CLI; cache results if safe + successful

### Classification Tiers (Safety-First)
1. **Authoritative**: `_get_authoritative_classification()` queries AWS Service Reference API for `IsWrite` flags
2. **IAM Heuristics**: Fallback pattern matching (`describe`, `list`, `get` = read; `create`, `delete`, `update` = write)
3. **Default**: Unknown operations → **no cache** + warning (fail safe)

### Key Methods
- `_get_cache_key()`: SHA256 of normalized args + AWS context (profile/region)
- `_normalize_aws_args()`: Sort flags alphabetically to ensure consistent cache hits regardless of arg order
- `_get_aws_context()`: Extract profile from `--profile` flag **or** `AWS_PROFILE` env (CLI flag takes precedence)
- `_determine_operation_type()`: Three-tier classification with caching of results
- `execute()`: Main entry point—check cache, run AWS CLI, write cache if safe

## Build and Test
- **Install**: `cp aws-cache ~/bin/aws-cache && chmod +x ~/bin/aws-cache`
- **Smoke Test**: `./aws-cache sts get-caller-identity` (run twice; second should be instant/cached)
- **Verify Cache**: `ls -la ~/.aws-cache/` to see cache files (JSON with command metadata)
- **Clear Cache**: `aws-cache --cache-clear`
- **Environment Test**: `AWS_PROFILE=myprofile ./aws-cache ec2 describe-instances` (verify profile isolation)

## Test-Driven Development (TDD)

All new features must follow strict Red-Green-Refactor (RGR) discipline:

### Red Phase
Write a **failing test first**—never implement code before the test exists. Tests define the contract. Run with `pytest tests/test_*.py -v` and verify FAIL status. Use skeleton test patterns from [NEXT_FEATURES.md](NEXT_FEATURES.md) as templates. Each test must be independent: isolated temp caches, mocked AWS CLI/APIs, no shared state.

### Green Phase
Write **minimal code** to make the test pass—no over-engineering. Implement only what the failing test requires. Run `pytest` again; tests must PASS. This proves the feature works as specified. Coverage doesn't need to be perfect yet; focus on making the test pass.

### Refactor Phase
**Improve code quality** without changing behavior. Extract duplicated logic, improve naming, optimize performance. Crucially: **all tests must still pass**. Run `pytest --cov=aws_cache tests/ --cov-report=term-missing` to verify coverage (target ≥ 85% overall, ≥ 95% for critical paths). Use separate atomic commits for each phase.

### Example: Cache Statistics Feature
```bash
# 1. RED: Copy test skeleton from NEXT_FEATURES.md → tests/test_cache_statistics.py
# 2. Run: pytest tests/test_cache_statistics.py -v  (expect 3 FAILURES)
# 3. GREEN: Implement _get_cache_stats() in AWSCache class (minimal code)
# 4. Run: pytest tests/test_cache_statistics.py -v  (expect 3 PASSES)
# 5. REFACTOR: Extract stats logic into helper method
# 6. Run: pytest tests/test_cache_statistics.py -v  (expect 3 PASSES + coverage check)
# 7. git add tests/ && git commit -m "RED: Add cache statistics tests"
# 8. git add aws-cache && git commit -m "GREEN: Implement cache stats feature"
# 9. git commit --amend -m "REFACTOR: Extract stats into AWSCache._compute_stats()"
```

### Mocking & Isolation
- **Subprocess**: Use `monkeypatch.setattr` or `unittest.mock.patch` for `subprocess.run()`
- **environ**: Use `monkeypatch.setenv()` or `patch.dict(os.environ)` for `AWS_PROFILE`, `AWS_CACHE_DIR`
- **urllib**: Mock `urllib.request.urlopen()` to stub AWS Service Reference API responses
- **Cache dir**: Each test gets isolated temp directory via `tmp_path` fixture
- **Never**: Use real AWS credentials, make real API calls, or write to `~/.aws-cache/`

### Coverage Requirements
- Overall: **≥ 85%** (catches regressions, not perfection)
- Critical paths (cache ops, classification): **≥ 95%** (bulletproof)
- Edge cases (errors, timeouts): **100%** (no surprises)
- Run: `pytest --cov=aws_cache --cov-report=html tests/` → view `htmlcov/index.html`

### Next Features (Priority Order)
See [NEXT_FEATURES.md](NEXT_FEATURES.md) for high-value features with skeleton Red-phase tests:
1. **Cache Statistics** (hits/misses, eviction tracking)
2. **Cache Invalidation by Pattern** (selective purge)
3. **Graceful Degradation** (fallback when APIs unavailable)
4. **Cache Compression** (gzip, LRU)
5. **Cache Versioning** (format migration)

### References
- [TESTING_STRATEGY.md](TESTING_STRATEGY.md) (653 lines: fixtures, mocking patterns, best practices)
- [TDD_SUMMARY.md](TDD_SUMMARY.md) (execution plan with weekly milestones)
- [README_TDD.md](README_TDD.md) (quick reference with priority matrix)

## Project Conventions
- **Safety over performance**: Always default to NO_CACHE for ambiguous cases
- **Context isolation**: Cache keyed on profile + region to prevent cross-account leakage
- **Argument normalization**: Flag order doesn't matter—both `--region x --output json` and `--output json --region x` hit same cache
- **Helpful feedback**: Auto-correct common mistakes (e.g., `aws-cache aws ...` removes redundant `aws`); warn on unknown operations
- **Version in VERSION variable**: Update before releases; referenced in `--version` and README

## Integration Points
- **AWS CLI**: Invoked as subprocess; assumes `aws` in PATH
- **AWS Service Reference API**: `https://servicereference.us-east-1.amazonaws.com/v1/{service}/*.json`
  - Essential services (sts, ec2, s3, iam) cached at startup; others on-demand
  - 7-day TTL for authoritative cache; stored in `~/.aws-cache/aws-service-reference.json`
- **AWS Config**: Fallback region lookup via `aws configure get region` (for cache context)

## Semantic Versioning
Follow **semver** (MAJOR.MINOR.PATCH):
- **MAJOR** (v1.0.0): Breaking changes (e.g., removed CLI flag, changed cache format/location)
- **MINOR** (v0.5.0): New features, new AWS services supported, backward compatible
- **PATCH** (v0.4.1): Bug fixes, performance improvements, documentation updates
- **Update VERSION variable** in [aws-cache](aws-cache#L61) before release
- **Tag commits** as `git tag v0.4.1 && git push origin v0.4.1`
- **Update README.md** Version History section with changelog entry

## Git Hygiene
Use the **Git Hygiene** custom agent to validate commit messages, branch naming, merge readiness, and release preparation. The agent is **read-only by design** and runs as a subagent to catch violations before they reach main.

**Quick tasks:**
- Validate commit messages before push: `@git-hygiene validate-commit "Your message here"`
- Check branch readiness for PR: `@git-hygiene validate-branch feature/your-branch`
- Audit commits for merge readiness: `@git-hygiene audit-merge main..your-branch`
- Prepare release with semver validation: `@git-hygiene prepare-release --to v0.5.0`

See [.github/agents/git-hygiene.agent.md](.github/agents/git-hygiene.agent.md) for full enforcement standards and remediation guidance.

## GitHub Workflow
- **Issues**: Describe classification failures (e.g., "operation X reported as read but is actually write") with minimal reproduction
- **PRs**: Include test output (before/after cache behavior); verify no regressions on safe operations
- **Releases**: Follow semver; tag after VERSION update; create release notes summarizing changes
- **CI/CD**: Consider adding: linting (pylint), cache isolation tests, AWS API mock tests for classification accuracy

## Notes for Contributors
- Modify only [aws-cache](aws-cache)—no separate modules
- Test with multiple AWS profiles and regions to verify isolation
- When adding features, maintain zero external dependency constraint
- Performance is secondary to correctness—always verify safety of cached operations
