"""Build a local reviewable submission bundle without publishing or sending anything."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", default="out/release-smoke")
    parser.add_argument("--scale", default="out/scale")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "submission" / "artifacts"
    destination.mkdir(parents=True, exist_ok=True)
    for label, source in (("smoke", args.smoke), ("scale", args.scale)):
        source = root / source
        report = json.loads((source / "run-report.json").read_text(encoding="utf-8"))
        if not report["validation"]["passed"]:
            raise SystemExit(f"Refusing to package failed {label} validation")
        if label == "smoke" and report["companies"] != 100:
            raise SystemExit("Smoke package must contain 100 companies")
        if label == "smoke":
            shutil.copytree(source, destination / label, dirs_exist_ok=True, ignore=shutil.ignore_patterns("checkpoint.jsonl"))
        else:
            # Scale results are development evidence; no precomputed 1000-profile submission is needed.
            shutil.copy2(source / "run-report.json", destination / "scale-report.json")
    shutil.copy2(root / "data" / "smoke-input.jsonl", destination / "smoke-input.jsonl")
    shutil.copy2(root / "out" / "tests.xml", destination / "tests.xml")
    for name in ("external-audit.json",):
        shutil.copy2(root / "out" / name, destination / name)
    shutil.copy2(root / "out" / "scale-audited" / "run-report.json", destination / "scale-audited-report.json")
    shutil.copy2(root / "out" / "scale-refresh" / "run-report.json", destination / "refresh-replay-report.json")
    files = sorted(p for p in destination.rglob("*") if p.is_file())
    manifest = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (root / "submission" / "artifact-hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"artifact_files": len(files), "bytes": sum(p.stat().st_size for p in files)}))


if __name__ == "__main__":
    main()
