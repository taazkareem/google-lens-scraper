"""Unit tests for SessionManager."""

import json
from pathlib import Path
from unittest.mock import patch

from google_lens_scraper.config import LensConfig
from google_lens_scraper.session import SessionManager


def test_session_manager_save_and_load(tmp_path: Path):
    session_file = tmp_path / "session.json"
    sm = SessionManager(session_path=session_file)

    assert not sm.is_authenticated()
    assert sm.load_session() is None

    test_state = {
        "cookies": [
            {"name": "SOCS", "value": "test_socs", "domain": ".google.com", "path": "/"},
            {"name": "SID", "value": "test_sid", "domain": ".google.com", "path": "/"},
        ],
        "origins": [],
    }

    saved = sm.save_session(test_state)
    assert saved.exists()
    assert sm.is_authenticated()

    loaded = sm.load_session()
    assert loaded is not None
    assert len(loaded["cookies"]) == 2
    assert loaded["cookies"][0]["name"] == "SOCS"

    assert sm.clear_session()
    assert not session_file.exists()
    assert not sm.is_authenticated()


def test_session_manager_env_override(tmp_path: Path):
    session_file = tmp_path / "nonexistent.json"
    sm = SessionManager(session_path=session_file)

    env_state = {
        "cookies": [{"name": "NID", "value": "test_nid", "domain": ".google.com", "path": "/"}],
        "origins": [],
    }

    with patch.dict("os.environ", {"LENS_STORAGE_STATE_JSON": json.dumps(env_state)}):
        loaded = sm.load_session()
        assert loaded is not None
        assert loaded["cookies"][0]["name"] == "NID"
        assert sm.is_authenticated()


def test_lens_config_auto_loads_saved_session(tmp_path: Path):
    session_file = tmp_path / "session.json"
    sm = SessionManager(session_path=session_file)
    sm.save_session(
        {
            "cookies": [{"name": "SID", "value": "auth_sid", "domain": ".google.com", "path": "/"}],
            "origins": [],
        }
    )

    cfg = LensConfig(session_path=session_file, use_saved_session=True)
    cookies = cfg.get_playwright_cookies()
    assert len(cookies) == 3
    assert any(c["name"] == "SID" for c in cookies)
    assert any(c["name"] == "SOCS" for c in cookies)


def test_session_manager_base64_env(tmp_path: Path):
    import base64

    sm = SessionManager(session_path=tmp_path / "nonexistent.json")
    env_state = {
        "cookies": [{"name": "SID", "value": "b64_sid", "domain": ".google.com", "path": "/"}],
        "origins": [],
    }
    b64_str = base64.b64encode(json.dumps(env_state).encode("utf-8")).decode("utf-8")

    with patch.dict("os.environ", {"LENS_STORAGE_STATE_JSON": b64_str}):
        loaded = sm.load_session()
        assert loaded is not None
        assert loaded["cookies"][0]["value"] == "b64_sid"


def test_session_manager_dotenv_loading(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text('LENS_COOKIES="SOCS=dotenv_socs; SID=dotenv_sid"\n', encoding="utf-8")

    sm = SessionManager(session_path=tmp_path / "nonexistent.json")
    with patch.dict("os.environ", {}, clear=True):
        loaded = sm.load_session()
        assert loaded is not None
        names = {c["name"] for c in loaded["cookies"]}
        assert "SOCS" in names
        assert "SID" in names


def test_write_env_file(tmp_path: Path, monkeypatch):
    from google_lens_scraper.cli import _write_env_file

    monkeypatch.chdir(tmp_path)
    env_file = _write_env_file("test_base64_payload")
    assert env_file.exists()
    content = env_file.read_text(encoding="utf-8")
    assert 'LENS_STORAGE_STATE_JSON="test_base64_payload"' in content

    # Test update
    _write_env_file("updated_base64_payload")
    content_updated = env_file.read_text(encoding="utf-8")
    assert 'LENS_STORAGE_STATE_JSON="updated_base64_payload"' in content_updated
    assert "test_base64_payload" not in content_updated
