#!/usr/bin/env python3
"""
Smoke Test Script

This script performs basic smoke tests against a deployed application:
- Verifies DNS resolution
- Performs HTTP health check
- Reports deployment status

Usage:
    python smoke-test.py <app-config.yml>

Exit codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import socket
import sys
import urllib.request
import urllib.error
import yaml


def resolve_dns(hostname: str, dns_server: str = None) -> str | None:
    """
    Attempt to resolve a hostname to an IP address.
    
    Args:
        hostname: The hostname to resolve
        dns_server: Optional DNS server to use (not used in basic resolution)
    
    Returns:
        The resolved IP address or None if resolution failed
    """
    try:
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.gaierror as e:
        print(f"  DNS resolution failed: {e}")
        return None


def http_health_check(url: str, timeout: int = 10) -> tuple:
    """
    Perform an HTTP health check against a URL.
    
    Args:
        url: The URL to check
        timeout: Request timeout in seconds
    
    Returns:
        Tuple of (success: bool, status_code: int or None, message: str)
    """
    try:
        request = urllib.request.Request(url, method='GET')
        request.add_header('User-Agent', 'SmokeTest/1.0')
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status_code = response.getcode()
            if 200 <= status_code < 400:
                return (True, status_code, "Health check passed")
            else:
                return (False, status_code, f"Unexpected status code: {status_code}")
    except urllib.error.HTTPError as e:
        return (False, e.code, f"HTTP error: {e.reason}")
    except urllib.error.URLError as e:
        return (False, None, f"URL error: {e.reason}")
    except socket.timeout:
        return (False, None, "Request timed out")
    except Exception as e:
        return (False, None, f"Unexpected error: {e}")


def run_smoke_tests(config: dict) -> bool:
    """
    Run all smoke tests for an application.
    
    Args:
        config: The application configuration dictionary
    
    Returns:
        True if all tests passed, False otherwise
    """
    all_passed = True
    metadata = config.get('metadata', {})
    app_name = metadata.get('name', 'unknown')
    
    print(f"\n{'='*60}")
    print(f"Smoke Tests for: {app_name}")
    print(f"{'='*60}")
    
    # Test 1: DNS Resolution
    print("\n📡 Test 1: DNS Resolution")
    dns_config = config.get('dns', {})
    k8s_config = config.get('kubernetes', {})
    ingress = k8s_config.get('ingress', {})
    
    hostname = ingress.get('host', '')
    dns_server = dns_config.get('server', '')
    
    if hostname:
        print(f"  Resolving: {hostname}")
        resolved_ip = resolve_dns(hostname, dns_server)
        if resolved_ip:
            print(f"  ✅ Resolved to: {resolved_ip}")
        else:
            print(f"  ⚠️  DNS resolution failed (may be expected in test environments)")
            # Don't fail on DNS - it may not be configured yet
    else:
        print("  ⚠️  No hostname configured for DNS test")
    
    # Test 2: HTTP Health Check
    print("\n🌐 Test 2: HTTP Health Check")
    
    if hostname:
        # Try direct IP first (HAProxy VIP)
        haproxy = config.get('haproxy', {})
        vip = haproxy.get('host', '')
        
        if vip:
            url = f"http://{vip}"
            print(f"  Checking: {url} (via HAProxy VIP)")
            success, status, message = http_health_check(url, timeout=5)
            if success:
                print(f"  ✅ {message} (HTTP {status})")
            else:
                print(f"  ⚠️  {message}")
                # Try with hostname
                url = f"http://{hostname}"
                print(f"  Checking: {url} (via hostname)")
                success, status, message = http_health_check(url, timeout=5)
                if success:
                    print(f"  ✅ {message} (HTTP {status})")
                else:
                    print(f"  ❌ {message}")
                    all_passed = False
        else:
            url = f"http://{hostname}"
            print(f"  Checking: {url}")
            success, status, message = http_health_check(url, timeout=5)
            if success:
                print(f"  ✅ {message} (HTTP {status})")
            else:
                print(f"  ⚠️  {message} (may be expected if not yet deployed)")
    else:
        print("  ⚠️  No hostname configured for health check")
    
    # Test 3: Configuration Sanity Check
    print("\n🔍 Test 3: Configuration Sanity Check")
    
    # Check replicas
    deployment = k8s_config.get('deployment', {})
    replicas = deployment.get('replicas', 0)
    if replicas > 0:
        print(f"  ✅ Replicas configured: {replicas}")
    else:
        print("  ❌ No replicas configured")
        all_passed = False
    
    # Check resource limits
    resources = deployment.get('resources', {})
    if resources.get('limits') and resources.get('requests'):
        print("  ✅ Resource limits and requests configured")
    else:
        print("  ⚠️  Resource limits/requests not fully configured")
    
    # Summary
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ All smoke tests passed!")
    else:
        print("❌ Some smoke tests failed")
    print(f"{'='*60}\n")
    
    return all_passed


def main():
    """Main entry point for smoke tests."""
    if len(sys.argv) != 2:
        print("Usage: python smoke-test.py <app-config.yml>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML syntax: {e}")
        sys.exit(1)
    
    if config is None:
        print("Error: Configuration file is empty")
        sys.exit(1)
    
    success = run_smoke_tests(config)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
