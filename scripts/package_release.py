"""Package validated run outputs into submission/release/. Does not publish or submit anything.

Only snapshots referenced by envelope evidence are copied; transient discovery pages
(for example the NAV feed index) are not evidence and stay in the local run folder.
"""
import argparse
import gzip
import hashlib
import json
import re
import shutil
from pathlib import Path

from orglens.core import read_inputs, validate


def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def copy_run(source, destination, input_path, with_snapshots=True):
    rows = load(source / "envelopes.jsonl")
    check = validate(rows, read_inputs(input_path), source / "snapshots")
    if not check["passed"]:
        raise SystemExit(f"Refusing invalid run {source}: {check['errors'][:3]}")
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("envelopes.jsonl", "run-report.json", "index.html"):
        shutil.copy2(source / name, destination / name)
    shutil.copy2(input_path, destination / "input.jsonl")
    if with_snapshots:
        (destination / "snapshots").mkdir(exist_ok=True)
        for sha in sorted({s["content_sha256"] for r in rows for s in r["source_snapshots"]}):
            shutil.copy2(source / "snapshots" / f"{sha}.bin", destination / "snapshots" / f"{sha}.bin")
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", required=True)
    parser.add_argument("--smoke-input", required=True)
    parser.add_argument("--refresh")
    parser.add_argument("--scale")
    parser.add_argument("--scale-input")
    parser.add_argument("--tests")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = root / "submission" / "release"
    if out.exists():
        shutil.rmtree(out)
    summary = {"smoke_companies": copy_run(root / args.smoke, out / "smoke", root / args.smoke_input)}
    if args.refresh:
        summary["refresh_companies"] = copy_run(root / args.refresh, out / "refresh", root / args.smoke_input)
    if args.scale:
        # 1,000+ profiles: envelopes, report and viewer; raw snapshots stay in the local run directory.
        summary["scale_profiles"] = copy_run(root / args.scale, out / "scale", root / args.scale_input, with_snapshots=False)
        plain = out / "scale" / "envelopes.jsonl"
        with plain.open("rb") as source, gzip.open(str(plain) + ".gz", "wb", compresslevel=9) as target:
            shutil.copyfileobj(source, target)
        plain.unlink()
    if args.tests:
        shutil.copy2(root / args.tests, out / "tests.xml")
    credentials = []
    env = root / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
            if match and any(k in match[1].upper() for k in ("KEY", "TOKEN", "SECRET")):
                value = match[2].strip().strip("\"'").encode()
                if len(value) > 8:
                    credentials.append(value)
    files = sorted(p for p in out.rglob("*") if p.is_file())
    if any(secret in p.read_bytes() for p in files for secret in credentials):
        shutil.rmtree(out)
        raise SystemExit("Credential leak detected; package removed")
    manifest = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (out / "artifact-hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({**summary, "files": len(files), "credential_leak_check": "passed", "published": False}))


if __name__ == "__main__":
    main()
