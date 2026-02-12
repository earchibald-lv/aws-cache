"""Tests for AWS context and profile handling."""
import os
import sys
from pathlib import Path

from aws_cache import AWSCache


def test_extract_profile_from_args():
    """Test extracting profile from --profile CLI argument."""
    cache = AWSCache()
    
    # Test --profile flag with value
    args = ["ec2", "describe-instances", "--profile", "prod"]
    profile = cache._extract_profile_from_args(args)
    assert profile == "prod"
    
    # Test --profile=value format
    args = ["ec2", "describe-instances", "--profile=staging"]
    profile = cache._extract_profile_from_args(args)
    assert profile == "staging"


def test_profile_precedence_cli_over_env():
    """Test that --profile CLI arg takes precedence over AWS_PROFILE env."""
    cache = AWSCache()
    
    # Set environment variable
    os.environ["AWS_PROFILE"] = "env-profile"
    
    # CLI arg should take precedence
    args = ["ec2", "describe-instances", "--profile", "cli-profile"]
    context = cache._get_aws_context(args)
    
    assert context["profile"] == "cli-profile"
    
    # Cleanup
    del os.environ["AWS_PROFILE"]


def test_profile_from_env_when_no_cli():
    """Test that AWS_PROFILE env is used when no --profile CLI arg."""
    cache = AWSCache()
    
    os.environ["AWS_PROFILE"] = "env-profile"
    
    args = ["ec2", "describe-instances"]
    context = cache._get_aws_context(args)
    
    assert context["profile"] == "env-profile"
    
    # Cleanup
    del os.environ["AWS_PROFILE"]


def test_profile_defaults_to_default():
    """Test that profile defaults to 'default' when unset."""
    cache = AWSCache()
    
    # Ensure env var is not set
    if "AWS_PROFILE" in os.environ:
        del os.environ["AWS_PROFILE"]
    
    args = ["ec2", "describe-instances"]
    context = cache._get_aws_context(args)
    
    assert context["profile"] == "default"


def test_normalize_aws_args():
    """Test argument normalization for consistent cache keys."""
    cache = AWSCache()
    
    # Different flag orders should normalize to same result
    args1 = ["ec2", "describe-instances", "--region", "us-west-2", "--output", "json"]
    args2 = ["ec2", "describe-instances", "--output", "json", "--region", "us-west-2"]
    
    normalized1 = cache._normalize_aws_args(args1)
    normalized2 = cache._normalize_aws_args(args2)
    
    assert normalized1 == normalized2
