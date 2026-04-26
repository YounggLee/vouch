from vouch import cache


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    cache.save("stage_x", "payload-1", {"a": 1, "b": [2, 3]})
    assert cache.load("stage_x", "payload-1") == {"a": 1, "b": [2, 3]}


def test_load_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    assert cache.load("stage_x", "missing") is None


def test_fallback_to_stage_json(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    (tmp_path / "stage_x.json").write_text('[{"id": "fallback"}]')
    assert cache.load("stage_x", "any-payload") == [{"id": "fallback"}]


def test_hashed_key_takes_precedence_over_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "_CACHE_DIR", tmp_path)
    cache.save("stage_x", "payload-A", {"hashed": True})
    (tmp_path / "stage_x.json").write_text('{"hashed": false}')
    assert cache.load("stage_x", "payload-A") == {"hashed": True}
