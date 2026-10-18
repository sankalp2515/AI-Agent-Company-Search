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
