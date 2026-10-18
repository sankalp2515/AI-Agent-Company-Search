from scripts.compare_public_reference import url_key


def test_facebook_profile_identity_is_not_lost_when_comparing_reference_urls():
    assert url_key('https://facebook.com/profile.php?id=123') != url_key('https://facebook.com/profile.php?id=456')
    assert url_key('https://www.facebook.com/profile.php?id=123&utm_source=site') == url_key('https://facebook.com/profile.php?id=123')
