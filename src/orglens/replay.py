"""Repeat extraction against actual saved source bytes without pretending they are fresh."""
import json
from pathlib import Path

from .core import Transport, digest


class ReplayTransport(Transport):
    def __init__(self, root, source, requests, seconds):
        super().__init__(root, requests, seconds)
        self.source = Path(source)
        self.index = {}
        for line in (self.source / "envelopes.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            for snap in row["source_snapshots"]:
                self.index.setdefault(snap.get("requested_url", snap["source_url"]), snap)

    def get(self, url, source_class="official_registry"):
        snap = self.index.get(url)
        if not snap:
            return {"status": 0, "source_url": url, "retrieved_at": "not_retrieved", "error": "No saved observation for this URL; replay never uses the network"}
        raw = (self.source / "snapshots" / (snap["content_sha256"] + ".bin")).read_bytes()
        if digest(raw) != snap["content_sha256"]:
            raise ValueError("Replay source hash mismatch")
        path = self.root / (snap["content_sha256"] + ".bin")
        if not path.exists():
            path.write_bytes(raw)
        return {**snap, "text": raw.decode(snap.get("charset") or "utf-8", errors="replace"), "replayed": True}
