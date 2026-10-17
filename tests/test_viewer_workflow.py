"""Execute the generated viewer script against a small DOM boundary double.

These test workflow state and safe element construction, not browser layout.
Actual responsive/keyboard verification still requires a browser.
"""
import json
import re
import shutil
import subprocess

import pytest

from orglens.core import envelope, finish
from orglens.viewer import render


DOM = r"""
const assert = require('node:assert/strict');
class Element {
  constructor(tag) { this.tagName=tag; this.children=[]; this.value=''; this._text=''; }
  set textContent(value) { this._text=String(value); this.children=[]; }
  get textContent() { return this._text + this.children.map(c=>c.textContent).join(''); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._text=''; this.children=children; }
  setAttribute(key,value) { this[key]=String(value); }
  click() { if(this.onclick) this.onclick(); }
}
const ids=Object.fromEntries(['data','search','filter','compare','download','stats','list','detail'].map(id=>[id,new Element('div')]));
ids.data.textContent=JSON.stringify(INPUT);
ids.filter.value='all';
const document={getElementById:id=>ids[id],createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text})};
const location={hash:''};
const descendants=n=>[n,...(n.children||[]).flatMap(descendants)];
"""


def row(number, name):
    value = finish(envelope(str(number), "viewer-test"))
    value["legal_identity"]["legal_name"] = name
    return value


def execute(tmp_path, rows, assertions):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to execute the generated viewer script")
    path = tmp_path / "index.html"
    render(rows, path)
    script = re.findall(r"<script>(.*?)</script>", path.read_text(encoding="utf-8"), re.S)[0]
    result = subprocess.run([node, "-"], input="const INPUT=" + json.dumps(rows) + ";\n" + DOM + script + "\n" + assertions,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_every_company_remains_selectable_above_500(tmp_path):
    execute(tmp_path, [row(100000000+i, f"Company {i}") for i in range(501)], """
assert.equal(ids.list.children.filter(n=>n.tagName==='button').length,501);
ids.list.children.at(-1).click();
assert.match(ids.detail.textContent,/Company 500/);
""")


def test_search_updates_profile_and_has_an_explicit_empty_state(tmp_path):
    execute(tmp_path, [row(123456789, "Alpha AS"), row(987654321, "Beta AS")], """
ids.search.value='Beta'; ids.search.oninput();
assert.match(ids.detail.textContent,/Beta AS/);
assert.doesNotMatch(ids.detail.textContent,/Alpha AS/);
ids.search.value='no such company'; ids.search.oninput();
assert.match(ids.list.textContent,/No companies match/);
assert.doesNotMatch(ids.detail.textContent,/Beta AS/);
""")


def test_stale_facts_show_previous_source_and_clearly_distinct_status(tmp_path):
    value = row(123456789, "Example AS")
    value["refresh"] = {"last_known_claims": [{"field": "official_website", "value": "https://example.no", "evidence_ids": ["old"]}],
                        "previous_evidence": [{"id": "old", "source_url": "https://registry.example.no/source", "retrieved_at": "2025-01-01", "identity_method": "official register"}]}
    execute(tmp_path, [value], """
const stale=descendants(ids.detail).find(n=>n.tagName==='h3' && /Last known facts/.test(n.textContent));
assert.ok(stale);
assert.match(ids.detail.textContent,/Not re-verified/);
assert.ok(descendants(ids.detail).some(n=>n.tagName==='a' && n.href==='https://registry.example.no/source'));
""")
