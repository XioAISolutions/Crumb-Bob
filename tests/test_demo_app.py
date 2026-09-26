"""Tests for the Streamlit demo app (streamlit_app.py).

Skipped automatically when streamlit is not installed (CI keeps core-only deps).
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit_app as app  # noqa: E402


def test_assets_present():
    assert app.SAMPLE_REPORT.exists(), "bundled sample report missing"
    assert app.DEMO_DB.exists(), "bundled demo DB missing"
    assert app.DEMO_PACK.exists(), "bundled demo pack missing"


def test_generate_and_verify(tmp_path):
    pack_dir = app.generate_pack(app.SAMPLE_REPORT.read_text(), str(tmp_path))
    files = [f for f in app.PACK_FILES if (tmp_path / f).exists()]
    assert len(files) == 9, f"expected 9 pack files, got {files}"
    rows, pc = app.verify_pack(pack_dir)
    assert rows, "proof chain rows empty"
    assert all(r["ok"] for r in rows), f"unverified rows: {[r for r in rows if not r['ok']]}"
    assert pc.get("crumdbob_version")


def test_tamper_detected():
    rows = app.tamper_rows(str(app.DEMO_PACK))
    bad = [r["file"] for r in rows if not r["ok"]]
    assert "00_repo_genome.crumb" in bad, "tamper simulation was not detected"


def test_db_readable():
    info = app.db_introspect(str(app.DEMO_DB))
    names = {i["table"] for i in info}
    assert "sessions" in names
    assert any(i["table"] == "sessions" and i["rows"] >= 1 for i in info)
    prev = app.db_preview(str(app.DEMO_DB), "sessions")
    assert prev, "sessions preview empty"


def test_zip_pack():
    data = app.zip_pack(str(app.DEMO_PACK))
    assert len(data) > 1000
