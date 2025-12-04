#!/usr/bin/env python3
"""
YAML to JSON Converter

Reads a YAML file and outputs JSON to stdout for use with Ansible extra vars.

Usage:
    python yaml-to-json.py <yaml-file>
"""

import json
import sys
import yaml


def main():
    """Convert YAML file to JSON output."""
    if len(sys.argv) != 2:
        print("Usage: python yaml-to-json.py <yaml-file>", file=sys.stderr)
        sys.exit(1)
    
    yaml_file = sys.argv[1]
    
    try:
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        print(json.dumps(data))
    except FileNotFoundError:
        print(f"Error: File not found: {yaml_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
