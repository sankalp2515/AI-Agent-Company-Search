from orglens.discovery import name_ranked


def test_host_matching_the_legal_name_is_inspected_first():
    found = ["https://www.porten.no/tag/haukaasen/", "https://biztrac.no/selskap/829275872",
             "https://www.haukasenlodge.no/", "https://ut.no/kart/tur/1"]
    assert name_ranked(found, "HAUKÅSEN FJELLGARD AS")[0] == "https://www.haukasenlodge.no/"


def test_order_is_unchanged_without_a_distinctive_name_word():
    found = ["https://a.no/", "https://b.no/"]
    assert name_ranked(found, "AS") == found
    assert name_ranked(found, "ZZZZ HOLDING AS") == found
