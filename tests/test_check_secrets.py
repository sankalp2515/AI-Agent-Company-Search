"""Security guard behavior; token samples are assembled synthetic strings."""
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_secrets.py"


def load_guard():
    assert SCRIPT.exists(), "tracked-file secret guard must exist"
    spec = importlib.util.spec_from_file_location("check_secrets", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detects_common_credentials_without_printing_values(tmp_path, capsys):
    guard = load_guard()
    samples = {
        "google_api_key": "AIza" + "Abc9_-z" * 5,
        "aws_access_key": "AKIA" + "AB12CD34EF56GH78",
        "github_token": "ghp_" + "abcdef123456" * 3,
        "openai_token": "sk-proj-" + "Abc123xyz_" * 5,
        "jwt": "eyJhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiJleGFtcGxlIn0" + "." + "AbCd1234_" * 4,
        "private_key": "-----BEGIN " + "RSA PRIVATE KEY-----",
    }
    for expected, token in samples.items():
        path = tmp_path / (expected + ".txt")
        path.write_text(token, encoding="utf-8")
        assert expected in guard.scan_file(path, {})
    assert capsys.readouterr().out == ""


def test_synthetic_fixture_does_not_allow_real_token_on_same_line(tmp_path):
    guard = load_guard()
    path = tmp_path / "fixture.py"
    path.write_text("AIza" + "A" * 35, encoding="utf-8")
    assert guard.scan_file(path, {}) == {}
    path.write_text("AIza" + "A" * 35 + " real=" + "AIza" + "Abc9_-z" * 5, encoding="utf-8")
    assert guard.scan_file(path, {}) == {"google_api_key": 1}


def test_known_private_value_detected_even_without_common_pattern(tmp_path):
    guard = load_guard()
    path = tmp_path / "blob.bin"
    token = "private-account-" + "value-for-test"
    path.write_bytes(b"\xff\0" + token.encode())
    assert guard.scan_file(path, {"CUSTOM_API_KEY": token}) == {"configured_private_value": 1}


def test_cli_scans_only_listed_files_and_rejects_public_raw_snapshot(tmp_path, capsys):
    guard = load_guard()
    (tmp_path / "safe.txt").write_text("safe", encoding="utf-8")
    (tmp_path / ".env").write_text("CUSTOM_API_KEY=private-account-test-value\nENDPOINT=https://safe.example\n", encoding="utf-8")
    files = tmp_path / "tracked.txt"
    files.write_text("safe.txt\n", encoding="utf-8")
    assert guard.main(["--root", str(tmp_path), "--file-list", str(files)]) == 0
    snapshot = tmp_path / "submission" / "release" / "smoke" / "snapshots" / "x.bin"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b"harmless but unpublished evidence")
    files.write_text(snapshot.relative_to(tmp_path).as_posix() + "\nsafe.txt\n", encoding="utf-8")
    assert guard.main(["--root", str(tmp_path), "--file-list", str(files)]) == 1
    assert "raw_snapshot" in capsys.readouterr().out


def test_cli_redacts_known_secret_and_rejects_paths_outside_root(tmp_path, capsys):
    guard = load_guard()
    token = "private-account-test-value"
    (tmp_path / ".env").write_text("CUSTOM_API_KEY=" + token, encoding="utf-8")
    (tmp_path / "leak.txt").write_text(token, encoding="utf-8")
    files = tmp_path / "tracked.txt"
    files.write_text("leak.txt\n../outside.txt\n", encoding="utf-8")
    assert guard.main(["--root", str(tmp_path), "--file-list", str(files)]) == 1
    output = capsys.readouterr().out
    assert token not in output
    assert "configured_private_value" in output
    assert "unsafe_path" in output
