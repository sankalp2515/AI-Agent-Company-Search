from pathlib import Path

from orglens.core import digest,envelope,finish,validate


def test_shared_snapshot_is_hashed_once_per_validation_but_rechecked_on_refresh(tmp_path,monkeypatch):
    raw=b'original evidence'
    sha=digest(raw)
    path=tmp_path/(sha+'.bin')
    path.write_bytes(raw)
    rows=[finish(envelope(org,'test')) for org in ['123456789','987654321']]
    for row in rows:
        row['source_snapshots']=[{'id':'shared','content_sha256':sha}]
    original=Path.read_bytes
    reads=[]
    def observed(self):
        reads.append(self)
        return original(self)
    monkeypatch.setattr(Path,'read_bytes',observed)
    assert validate(rows,['123456789','987654321'],tmp_path)['passed']
    assert reads==[path]
    path.write_bytes(b'changed evidence')
    assert not validate(rows,['123456789','987654321'],tmp_path)['passed']


def test_missing_snapshot_fails_validation(tmp_path):
    row=finish(envelope('123456789','test'))
    row['source_snapshots']=[{'id':'missing','content_sha256':digest(b'absent')}]
    assert not validate([row],['123456789'],tmp_path)['passed']
