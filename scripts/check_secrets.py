"""Scan an explicit tracked-file list without ever printing secret values.

Generate a UTF-8 list with ``git ls-files > out/tracked-files.txt`` then run
``python scripts/check_secrets.py --file-list out/tracked-files.txt``.
NUL-delimited lists (git ls-files -z) are also supported. No Git subprocess
or product dependencies are used. Raw published evidence is forbidden even
when it contains no recognized credential; preserve it in ignored local storage.
"""
import argparse
import json
import re
from pathlib import Path


PATTERNS = {
    "google_api_key": re.compile(rb"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"),
    "aws_access_key": re.compile(rb"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    "github_token": re.compile(rb"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})(?![A-Za-z0-9_])"),
    "openai_token": re.compile(rb"(?<![A-Za-z0-9_-])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,255}(?![A-Za-z0-9_-])"),
    "jwt": re.compile(rb"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{7,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{16,}(?![A-Za-z0-9_-])"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
}
PRIVATE_NAME = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)", re.I)


def synthetic_token(kind, token):
    """Only uniform-character placeholders qualify; no file or line exemptions."""
    if kind == "private_key":
        return False
    prefixes = {
        "google_api_key": (b"AIza",),
        "aws_access_key": (b"AKIA", b"ASIA"),
        "github_token": (b"github_pat_", b"ghp_", b"gho_", b"ghu_", b"ghs_", b"ghr_"),
        "openai_token": (b"sk-proj-", b"sk-svcacct-", b"sk-"),
    }
    for prefix in prefixes.get(kind, ()):
        if token.startswith(prefix):
            tail = token[len(prefix):]
            return len(set(tail)) == 1
    return False


def configured_values(path):
    """Read local .env values in memory; never include names/values in reports."""
    result = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.removeprefix("export ").split("=", 1)
        value = value.strip()
        if value.startswith(("'", '"')):
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end >= 0 else value[1:]
        else:
            value = value.split(" #", 1)[0].rstrip()
        if PRIVATE_NAME.search(name) and len(value) >= 8:
            result[name.strip()] = value
    return result


def scan_file(path, private_values):
    body = path.read_bytes()
    findings = {}
    for kind, pattern in PATTERNS.items():
        count = sum(not synthetic_token(kind, match.group()) for match in pattern.finditer(body))
        if count:
            findings[kind] = count
    count = sum(body.count(value.encode("utf-8")) for value in set(private_values.values()) if value)
    if count:
        findings["configured_private_value"] = count
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--file-list", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, help="Defaults to ROOT/.env")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    private_values = configured_values(args.env_file or root / ".env")
    raw = args.file_list.read_text(encoding="utf-8-sig")
    names = raw.split("\0") if "\0" in raw else raw.splitlines()
    reports = []
    scanned = 0
    for name in dict.fromkeys(names):
        if not name:
            continue
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            reports.append({"path": "<outside-root>", "findings": {"unsafe_path": 1}})
            continue
        relative = path.relative_to(root).as_posix()
        findings = {}
        if relative.startswith("submission/") and "snapshots" in Path(relative).parts:
            findings["raw_snapshot"] = 1
        try:
            findings.update(scan_file(path, private_values))
            scanned += 1
        except OSError:
            findings["unreadable_file"] = 1
        if findings:
            # Do not print exception messages, source lines, or matched values.
            reports.append({"path": relative, "findings": findings})
    print(json.dumps({"scanned_files": scanned, "findings": reports}, indent=2))
    return 1 if reports else 0


if __name__ == "__main__":
    raise SystemExit(main())
