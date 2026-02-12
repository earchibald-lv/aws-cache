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
- **Commit messages**: Use imperative mood ("Add profile extraction" not "Added profile extraction")
- **Atomic commits**: One logical change per commit; independent fixes in separate commits
- **Branch naming**: Use descriptive prefixes: `feature/`, `fix/`, `docs/` (e.g., `feature/authoritative-classification`)
- **Rebase before merge**: Keep history linear; rebase onto main before opening PR
- **PR descriptions**: Link related issues, explain why changes matter, include test evidence
- **No force pushes** to main; use squash merge for feature branches to keep history clean
- **Sign commits** (optional but recommended): `git commit -S` for GPG signing on releases

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
