from orglens.names import domain_is_full_name, text_contains_name
from orglens.core import corroborated, soup_text
from test_integrity_fixes import snapshot


def test_connectors_are_normalized_on_both_sides_of_full_name_match():
    assert text_contains_name('Welcome to Fjord og Fjell AS, specialists in outdoor equipment.','FJORD OG FJELL AS')
    assert text_contains_name('Klinikken i Sentrum supplies local health care.','KLINIKKEN I SENTRUM AS')
    assert not text_contains_name('Klinikken i Bergen supplies local health care.','KLINIKKEN I SENTRUM AS')
    assert not text_contains_name('Fjord og Fjell supplies equipment.','FJORD OG FJELL NORGE AS')
    assert domain_is_full_name('https://fjordogfjell.no/','FJORD OG FJELL AS')
    assert domain_is_full_name('https://klinikkenisentrum.no/','KLINIKKEN I SENTRUM AS')


def test_exact_trading_name_and_registered_phone_allow_missing_legal_suffix():
    html='<main><h1>Fjord og Fjell</h1><p>Call +47 2233 4455</p></main>'
    parsed,text=soup_text(html)
    result=corroborated({'navn':'FJORD OG FJELL AS','telefon':'22334455'},[(snapshot(html),parsed,text)])
    assert result and result[2]=='legal_name_and_registered_phone'
    assert result[1]['text_quote'] in text
    assert result[1]['text_quote']=='Fjord og Fjell'


def test_name_span_preserves_original_unicode_and_punctuation():
    from orglens.names import matched_name_span
    assert matched_name_span('Contact Sør & Sæter today.','SØR OG SÆTER AS')=='Sør & Sæter'


def test_numbered_legal_entity_is_not_the_parent_brand():
    assert not text_contains_name('Kinland invests in properties.','KINLAND I AS')
    assert not text_contains_name('Kinland i Oslo owns properties.','KINLAND I AS')
    assert text_contains_name('Contact Kinland I AS for this property.','KINLAND I AS')
    assert not domain_is_full_name('https://kinland.no/','KINLAND I AS')


def test_acquired_company_mention_and_shared_phone_do_not_prove_publisher():
    html='<title>ABS Entreprenør AS</title><h1>Om ABS Entreprenør AS</h1><p>ABS Entreprenør AS kjøpte opp Hans Sylte AS i 2017.</p><p>Hans: 913 54 831</p>'
    parsed,text=soup_text(html)
    assert corroborated({'navn':'HANS SYLTE AS','telefon':'91354831'},[(snapshot(html,'https://absentreprenor.no/'),parsed,text)]) is None
