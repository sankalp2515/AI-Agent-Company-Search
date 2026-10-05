"""Package audited AI test outputs locally. Does not publish or submit."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from orglens.core import read_inputs, validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--refresh", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    smoke = root / args.smoke
    rows = [json.loads(line) for line in (smoke / "envelopes.jsonl").read_text(encoding="utf-8").splitlines()]
    report = json.loads((smoke / "run-report.json").read_text(encoding="utf-8"))
    if len(rows) != 100 or not report.get("agent") or not validate(rows, read_inputs(root / args.input), smoke / "snapshots")["passed"]:
        raise SystemExit("Refusing invalid AI smoke artifacts")
    destination = root / "submission" / "ai-artifacts"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(smoke, destination / "smoke", dirs_exist_ok=True, ignore=shutil.ignore_patterns("checkpoint.jsonl"))
    shutil.copy2(root / args.input, destination / "smoke-input.jsonl")
    shutil.copy2(root / args.refresh / "run-report.json", destination / "refresh-report.json")
    refresh = [json.loads(line) for line in (root / args.refresh / "envelopes.jsonl").read_text(encoding="utf-8").splitlines()]
    (destination / "refresh-changes.json").write_text(json.dumps({"companies": len(refresh), "material_changes": sum(len(r["changes"]) for r in refresh), "mode": "saved_source_replay_not_fresh"}, indent=2), encoding="utf-8")
    shutil.copy2(root / "out" / "ai-tests.xml", destination / "tests.xml")
    if (root / "out" / "ai-final-scale-replay" / "run-report.json").is_file():
        shutil.copy2(root / "out" / "ai-final-scale-replay" / "run-report.json", destination / "scale-replay-report.json")
    # Match configured credential VALUES, never emit them. Do not scan/commit .env itself.
    credentials = []
    for line in (root / ".env").read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
        if match and ("KEY" in match[1].upper() or "TOKEN" in match[1].upper()):
            value = match[2].strip().strip("\"'").encode()
            if len(value) > 8:
                credentials.append(value)
    files = sorted(p for p in destination.rglob("*") if p.is_file())
    if any(secret in p.read_bytes() for p in files for secret in credentials):
        raise SystemExit("Credential leak detected in package; publication forbidden")
    manifest = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (destination / "artifact-hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"artifact_files": len(files), "configured_credential_leak_check": "passed", "published": False, "submitted": False}))


if __name__ == "__main__":
    main()
