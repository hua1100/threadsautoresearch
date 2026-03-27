import json
import tempfile
from pathlib import Path

from orchestrator.utils import read_json, write_json, sanitize_post_text


def test_read_write_json():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        path = Path(f.name)
    data = [{"id": "1", "text": "hello"}]
    write_json(path, data)
    result = read_json(path)
    assert result == data
    path.unlink()


def test_read_json_missing_file():
    result = read_json(Path("/tmp/nonexistent_12345.json"))
    assert result == []


def test_sanitize_post_text_removes_literal_newlines():
    raw = "Hello\\n\\nWorld"
    cleaned = sanitize_post_text(raw)
    assert "\\n" not in cleaned
    assert "Hello" in cleaned
    assert "World" in cleaned


def test_sanitize_post_text_trims_whitespace():
    raw = "  Hello World  "
    cleaned = sanitize_post_text(raw)
    assert cleaned == "Hello World"


def test_sanitize_post_text_collapses_blank_lines():
    raw = "Hello\n\n\n\nWorld"
    cleaned = sanitize_post_text(raw)
    assert "\n\n\n" not in cleaned
