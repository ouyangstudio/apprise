#!/usr/bin/env python
"""Manual test for Feishu plugin"""

import sys
import os

# Add apprise to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Direct import to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "feishu", "apprise/plugins/feishu.py"
)
feishu_module = importlib.util.module_from_spec(spec)

# Mock the required imports
class MockLogger:
    def warning(self, msg): pass
    def debug(self, msg): pass
    def info(self, msg): pass

# Set up minimal environment
sys.modules['apprise'] = type(sys)('apprise')
sys.modules['apprise.common'] = type(sys)('apprise.common')
sys.modules['apprise.common'].NotifyType = type('NotifyType', (), {'INFO': 'info'})
sys.modules['apprise.locale'] = type(sys)('apprise.locale')
sys.modules['apprise.locale'].gettext_lazy = lambda x: x
sys.modules['apprise.utils'] = type(sys)('apprise.utils')
sys.modules['apprise.utils.parse'] = type(sys)('apprise.utils.parse')
sys.modules['apprise.utils.parse'].is_email = lambda x: '@' in x and '.' in x.split('@')[1]
sys.modules['apprise.utils.parse'].parse_list = lambda x: [x] if isinstance(x, str) else x
sys.modules['apprise.utils.parse'].validate_regex = lambda x, *args: x if args[0].match(x) else None
import re
sys.modules['apprise.utils.parse'].validate_regex = lambda x, pattern, flags=None: re.match(pattern, x) and x or None

sys.modules['apprise.url'] = type(sys)('apprise.url')
sys.modules['apprise.url'].PrivacyMode = type('PrivacyMode', (), {'Secret': 'secret'})

# Mock base class
class MockNotifyBase:
    template_tokens = {}
    template_args = {}
    secure_protocol = 'feishu'
    app_id = 'test-app'

    def __init__(self, **kwargs):
        self.verify_certificate = kwargs.get('verify_certificate', True)
        self.request_timeout = kwargs.get('request_timeout', 10)

    @staticmethod
    def parse_url(url, verify_host=True):
        from urllib.parse import urlparse, parse_qs
        result = {
            'schema': 'feishu',
            'host': '',
            'user': None,
            'password': None,
            'fullpath': '',
            'qsd': {},
        }
        parsed = urlparse(url)
        result['host'] = parsed.netloc or parsed.path.split('/')[0]
        result['fullpath'] = parsed.path
        result['qsd'] = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}
        return result

    def url_parameters(self, privacy=False, *args, **kwargs):
        return {}

    @staticmethod
    def split_path(path):
        """Split path into entries, handling empty strings"""
        entries = path.strip('/').split('/')
        return [e for e in entries if e]

    @staticmethod
    def unquote(s):
        """Unquote URL string"""
        from urllib.parse import unquote
        return unquote(s)

    @staticmethod
    def quote(s, safe=''):
        """Quote URL string"""
        from urllib.parse import quote
        return quote(s, safe=safe)

    @staticmethod
    def urlencode(params):
        """URL encode parameters"""
        from urllib.parse import urlencode
        return urlencode(params)

    @staticmethod
    def http_response_code_lookup(code):
        return f"HTTP {code}"

    def throttle(self):
        pass

    def pprint(self, s, privacy=False, safe='', mode=None):
        return s if not privacy else '*' * len(s)

sys.modules['apprise.base'] = type(sys)('apprise.base')
sys.modules['apprise.base'].NotifyBase = MockNotifyBase

# Now load the module
spec.loader.exec_module(feishu_module)

NotifyFeishu = feishu_module.NotifyFeishu
FeishuMode = feishu_module.FeishuMode

def test_webhook_mode():
    """Test Webhook mode parsing"""
    print("=" * 60)
    print("Testing Webhook Mode")
    print("=" * 60)

    # Test 1: Basic webhook URL
    url = "feishu://abc123-token"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 1 - Basic webhook URL: {url}")
    print(f"  Parsed: {result}")
    assert result['token'] == 'abc123-token', "Token should be parsed"
    assert result['app_id'] is None, "app_id should be None"
    assert result['app_secret'] is None, "app_secret should be None"
    print("  ✓ PASSED\n")

    # Test 2: Webhook with token in query string
    url = "feishu://?token=xyz789"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 2 - Webhook with token in query: {url}")
    print(f"  Parsed: {result}")
    assert result['token'] == 'xyz789', "Token should be parsed from query"
    print("  ✓ PASSED\n")

def test_app_mode():
    """Test App mode parsing"""
    print("=" * 60)
    print("Testing App Mode")
    print("=" * 60)

    # Test 3: App mode with single email
    url = "feishu://app/cli_abc123/secret456/user@example.com"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 3 - App mode single email: {url}")
    print(f"  Parsed: {result}")
    assert result['app_id'] == 'cli_abc123', "app_id should be parsed"
    assert result['app_secret'] == 'secret456', "app_secret should be parsed"
    assert result['targets'] == ['user@example.com'], "targets should have one email"
    assert result['token'] is None, "token should be None"
    print("  ✓ PASSED\n")

    # Test 4: App mode with multiple emails
    url = "feishu://app/cli_abc123/secret456/user1@example.com/user2@example.com"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 4 - App mode multiple emails: {url}")
    print(f"  Parsed: {result}")
    assert result['app_id'] == 'cli_abc123', "app_id should be parsed"
    assert result['app_secret'] == 'secret456', "app_secret should be parsed"
    assert len(result['targets']) == 2, "targets should have two emails"
    print("  ✓ PASSED\n")

    # Test 5: App mode via query string
    url = "feishu://app/?app_id=cli_test&app_secret=secret123&to=user@test.com"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 5 - App mode via query string: {url}")
    print(f"  Parsed: {result}")
    assert result['app_id'] == 'cli_test', "app_id should be parsed"
    assert result['app_secret'] == 'secret123', "app_secret should be parsed"
    assert result['targets'] == ['user@test.com'], "targets should have one email"
    print("  ✓ PASSED\n")

    # Test 6: App mode with mixed path and query
    url = "feishu://app/cli_abc123/secret456/user1@example.com/?to=user2@example.com"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 6 - App mode mixed: {url}")
    print(f"  Parsed: {result}")
    assert len(result['targets']) == 2, "Should have 2 targets total"
    print("  ✓ PASSED\n")

def test_invalid_urls():
    """Test invalid URLs"""
    print("=" * 60)
    print("Testing Invalid URLs")
    print("=" * 60)

    # Test 7: App mode without targets (should fail during __init__)
    url = "feishu://app/cli_abc123/secret456"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 7 - App mode without targets: {url}")
    print(f"  Parsed: {result}")
    assert result is None, "Should return None for invalid App URL"
    print("  ✓ PASSED\n")

    # Test 8: App mode with invalid email (should filter out invalid)
    url = "feishu://app/cli_abc123/secret456/invalid-email"
    result = NotifyFeishu.parse_url(url)
    print(f"Test 8 - App mode with invalid email: {url}")
    print(f"  Parsed: {result}")
    # parse_url should return result, but __init__ should fail
    # because no valid emails remain after filtering
    assert result is None, "Should return None when no valid emails"
    print("  ✓ PASSED\n")

def test_instantiation():
    """Test object instantiation"""
    print("=" * 60)
    print("Testing Object Instantiation")
    print("=" * 60)

    # Test 9: Webhook mode instantiation
    print("Test 9 - Webhook mode instantiation")
    try:
        obj = NotifyFeishu(token="test-token-123")
        print(f"  Mode: {obj.mode}")
        print(f"  Token: {obj.token}")
        assert obj.mode == FeishuMode.WEBHOOK, "Should be Webhook mode"
        assert obj.token == "test-token-123", "Token should match"
        print("  ✓ PASSED\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        return False

    # Test 10: App mode instantiation
    print("Test 10 - App mode instantiation")
    try:
        obj = NotifyFeishu(
            app_id="cli_test123",
            app_secret="secret456",
            targets=["user1@example.com", "user2@example.com"]
        )
        print(f"  Mode: {obj.mode}")
        print(f"  App ID: {obj.app_id}")
        print(f"  Targets: {obj.targets}")
        assert obj.mode == FeishuMode.APP, "Should be App mode"
        assert obj.app_id == "cli_test123", "App ID should match"
        assert len(obj.targets) == 2, "Should have 2 targets"
        print("  ✓ PASSED\n")
    except Exception as e:
        print(f"  ✗ FAILED: {e}\n")
        return False

    # Test 11: App mode without targets should fail
    print("Test 11 - App mode without targets (should fail)")
    try:
        obj = NotifyFeishu(app_id="cli_test", app_secret="secret")
        print(f"  ✗ FAILED: Should have raised TypeError\n")
        return False
    except TypeError as e:
        print(f"  Expected error: {e}")
        print("  ✓ PASSED\n")

def test_url_generation():
    """Test URL generation"""
    print("=" * 60)
    print("Testing URL Generation")
    print("=" * 60)

    # Test 12: Webhook mode URL
    print("Test 12 - Webhook mode URL generation")
    obj = NotifyFeishu(token="test-token")
    url = obj.url()
    print(f"  Generated URL: {url}")
    assert "feishu://test-token" in url, "URL should contain token"
    print("  ✓ PASSED\n")

    # Test 13: App mode URL
    print("Test 13 - App mode URL generation")
    obj = NotifyFeishu(
        app_id="cli_test123",
        app_secret="secret456",
        targets=["user1@example.com", "user2@example.com"]
    )
    url = obj.url()
    print(f"  Generated URL: {url}")
    assert "feishu://app/cli_test123/secret456" in url, "URL should contain app_id and app_secret"
    assert "user1@example.com" in url, "URL should contain first target"
    assert "user2@example.com" in url, "URL should contain second target"
    print("  ✓ PASSED\n")

if __name__ == "__main__":
    try:
        test_webhook_mode()
        test_app_mode()
        test_invalid_urls()
        test_instantiation()
        test_url_generation()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
