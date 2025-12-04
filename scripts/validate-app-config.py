#!/usr/bin/env python3
"""
Application Configuration Validator

This script validates the application YAML configuration files to ensure
they have all required fields and proper structure before deployment.

Usage:
    python validate-app-config.py <app-config.yml>

Exit codes:
    0 - Validation successful
    1 - Validation failed
"""

import sys
import re
import yaml


def validate_ip_address(ip: str) -> bool:
    """Validate an IPv4 address format."""
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    octets = ip.split('.')
    return all(0 <= int(octet) <= 255 for octet in octets)


def validate_dns_name(name: str) -> bool:
    """Validate a DNS hostname format."""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$'
    return bool(re.match(pattern, name))


def validate_fqdn(fqdn: str) -> bool:
    """Validate a fully qualified domain name."""
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    return bool(re.match(pattern, fqdn))


def validate_metadata(config: dict) -> list:
    """Validate the metadata section of the configuration."""
    errors = []
    
    if 'metadata' not in config:
        errors.append("Missing required section: metadata")
        return errors
    
    metadata = config['metadata']
    required_fields = ['name', 'environment', 'owner']
    
    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")
        elif not metadata[field]:
            errors.append(f"Metadata field '{field}' cannot be empty")
    
    return errors


def validate_dns(config: dict) -> list:
    """Validate the DNS section of the configuration."""
    errors = []
    
    if 'dns' not in config:
        errors.append("Missing required section: dns")
        return errors
    
    dns = config['dns']
    required_fields = ['provider', 'zone', 'server', 'records']
    
    for field in required_fields:
        if field not in dns:
            errors.append(f"Missing required DNS field: {field}")
    
    if 'server' in dns and not validate_ip_address(dns['server']):
        errors.append(f"Invalid DNS server IP address: {dns['server']}")
    
    if 'records' in dns:
        for i, record in enumerate(dns['records']):
            if 'type' not in record:
                errors.append(f"DNS record {i}: missing 'type' field")
            if 'name' not in record:
                errors.append(f"DNS record {i}: missing 'name' field")
            if 'value' not in record:
                errors.append(f"DNS record {i}: missing 'value' field")
            
            if record.get('type') == 'A' and 'value' in record:
                if not validate_ip_address(record['value']):
                    errors.append(f"DNS record {i}: invalid A record IP: {record['value']}")
            
            if 'name' in record and not validate_dns_name(record['name']):
                errors.append(f"DNS record {i}: invalid DNS name: {record['name']}")
    
    return errors


def validate_haproxy(config: dict) -> list:
    """Validate the HAProxy section of the configuration."""
    errors = []
    
    if 'haproxy' not in config:
        errors.append("Missing required section: haproxy")
        return errors
    
    haproxy = config['haproxy']
    
    if 'host' in haproxy and not validate_ip_address(haproxy['host']):
        errors.append(f"Invalid HAProxy host IP address: {haproxy['host']}")
    
    if 'frontend' not in haproxy:
        errors.append("Missing required HAProxy field: frontend")
    else:
        frontend = haproxy['frontend']
        frontend_required = ['name', 'bind_port', 'mode']
        for field in frontend_required:
            if field not in frontend:
                errors.append(f"Missing required HAProxy frontend field: {field}")
    
    if 'backend' not in haproxy:
        errors.append("Missing required HAProxy field: backend")
    else:
        backend = haproxy['backend']
        backend_required = ['name', 'mode', 'balance', 'servers']
        for field in backend_required:
            if field not in backend:
                errors.append(f"Missing required HAProxy backend field: {field}")
        
        if 'servers' in backend:
            for i, server in enumerate(backend['servers']):
                if 'address' in server and not validate_ip_address(server['address']):
                    errors.append(f"Backend server {i}: invalid IP: {server['address']}")
    
    return errors


def validate_kubernetes(config: dict) -> list:
    """Validate the Kubernetes section of the configuration."""
    errors = []
    
    if 'kubernetes' not in config:
        errors.append("Missing required section: kubernetes")
        return errors
    
    k8s = config['kubernetes']
    required_sections = ['namespace', 'deployment', 'service', 'ingress']
    
    for section in required_sections:
        if section not in k8s:
            errors.append(f"Missing required Kubernetes section: {section}")
    
    if 'deployment' in k8s:
        deployment = k8s['deployment']
        deployment_required = ['name', 'replicas', 'image']
        for field in deployment_required:
            if field not in deployment:
                errors.append(f"Missing required deployment field: {field}")
        
        if 'replicas' in deployment and not isinstance(deployment['replicas'], int):
            errors.append("Deployment replicas must be an integer")
        
        if 'replicas' in deployment and deployment['replicas'] < 1:
            errors.append("Deployment replicas must be at least 1")
    
    if 'service' in k8s:
        service = k8s['service']
        service_required = ['name', 'type', 'port']
        for field in service_required:
            if field not in service:
                errors.append(f"Missing required service field: {field}")
    
    if 'ingress' in k8s:
        ingress = k8s['ingress']
        ingress_required = ['name', 'host', 'path']
        for field in ingress_required:
            if field not in ingress:
                errors.append(f"Missing required ingress field: {field}")
        
        if 'host' in ingress and not validate_fqdn(ingress['host']):
            errors.append(f"Invalid ingress host FQDN: {ingress['host']}")
    
    return errors


def main():
    """Main entry point for the validator."""
    if len(sys.argv) != 2:
        print("Usage: python validate-app-config.py <app-config.yml>")
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
    
    # Run all validators
    all_errors = []
    all_errors.extend(validate_metadata(config))
    all_errors.extend(validate_dns(config))
    all_errors.extend(validate_haproxy(config))
    all_errors.extend(validate_kubernetes(config))
    
    if all_errors:
        print(f"Validation failed for {config_file}:")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print(f"✅ Validation successful: {config_file}")
    sys.exit(0)


if __name__ == '__main__':
    main()
