from sn_lib.cli import emit_json


def test_emit_json_writes_utf8_without_bom(tmp_path):
    out = tmp_path / "out.json"
    emit_json({"text": "zero-width \u200b and unicode \u03bc"}, str(out))
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    text = out.read_text(encoding="utf-8")
    assert "zero-width \u200b and unicode \u03bc" in text
