#!/usr/bin/env python
"""Simple validation of feishu.py syntax and structure"""

import ast
import re
import sys

def validate_python_syntax(filepath):
    """Validate Python syntax"""
    print("Validating Python syntax...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        print("[PASS] Python syntax is valid")
        return True
    except SyntaxError as e:
        print(f"[FAIL] Syntax error: {e}")
        return False

def check_structure(filepath):
    """Check code structure"""
    print("\nChecking code structure...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'FeishuMode class': r'class FeishuMode:',
        'NotifyFeishu class': r'class NotifyFeishu\(NotifyBase\):',
        'WEBHOOK mode': r'WEBHOOK = "webhook"',
        'APP mode': r'APP = "app"',
        'token cache': r'_tenant_token_cache = {}',
        'token method': r'def _get_tenant_access_token\(self\):',
        'send webhook method': r'def _send_webhook\(self',
        'send app method': r'def _send_app\(self',
        'parse_url method': r'def parse_url\(url\):',
        'app token url': r'app_token_url = ',
        'app message url': r'app_message_url = ',
        '__len__ method': r'def __len__\(self\):',
    }

    all_passed = True
    for check_name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"  [OK] {check_name} found")
        else:
            print(f"  [MISS] {check_name} NOT found")
            all_passed = False

    return all_passed

def check_url_patterns(filepath):
    """Check URL patterns in templates"""
    print("\nChecking URL templates...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for template definitions
    if 'templates = (' in content and '"{schema}://{token}/"' in content:
        print("  [OK] Webhook template found")
    else:
        print("  [FAIL] Webhook template NOT found")
        return False

    if '"{schema}://app/{app_id}/{app_secret}/{targets}/"' in content:
        print("  [OK] App mode template found")
    else:
        print("  [FAIL] App mode template NOT found")
        return False

    return True

def check_mode_detection(filepath):
    """Check mode detection logic"""
    print("\nChecking mode detection logic...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        ('entries[0].lower() == "app"', 'Path-based app detection'),
        ('self.mode = FeishuMode.WEBHOOK', 'Webhook mode assignment'),
        ('self.mode = FeishuMode.APP', 'App mode assignment'),
    ]

    all_passed = True
    for pattern, description in checks:
        if pattern in content:
            print(f"  [OK] {description}")
        else:
            print(f"  [MISS] {description} NOT found")
            all_passed = False

    return all_passed

def check_imports(filepath):
    """Check required imports"""
    print("\nChecking imports...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    required_imports = [
        'from json import dumps, loads',
        'from time import time',
        'from ..utils.parse import is_email, parse_list',
    ]

    all_passed = True
    for imp in required_imports:
        if imp in content:
            print(f"  [OK] {imp}")
        else:
            print(f"  [MISS] {imp} NOT found")
            all_passed = False

    return all_passed

if __name__ == "__main__":
    filepath = "apprise/plugins/feishu.py"

    print("=" * 60)
    print("Feishu Plugin Validation")
    print("=" * 60)

    results = []
    results.append(("Syntax", validate_python_syntax(filepath)))
    results.append(("Structure", check_structure(filepath)))
    results.append(("URL Templates", check_url_patterns(filepath)))
    results.append(("Mode Detection", check_mode_detection(filepath)))
    results.append(("Imports", check_imports(filepath)))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("ALL CHECKS PASSED!")
        sys.exit(0)
    else:
        print("SOME CHECKS FAILED!")
        sys.exit(1)
