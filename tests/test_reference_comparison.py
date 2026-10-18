import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    'compare_public_reference', Path(__file__).resolve().parents[1] / 'scripts' / 'compare_public_reference.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
url_key = comparison.url_key


def test_facebook_profile_identity_is_not_lost_when_comparing_reference_urls():
    assert url_key('https://facebook.com/profile.php?id=123') != url_key('https://facebook.com/profile.php?id=456')
    assert url_key('https://www.facebook.com/profile.php?id=123&utm_source=site') == url_key('https://facebook.com/profile.php?id=123')
