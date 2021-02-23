from tuxmake import cache


class TestCache:
    def test_roundtrip(self):
        cache.set("foo", "bar")
        assert cache.get("foo") == "bar"

    def test_missing_key(self):
        assert cache.get("missing") is None

    def test_composite_key(self):
        cache.set(["foo", "bar"], "baz")
        assert cache.get(["foo", "bar"]) == "baz"
