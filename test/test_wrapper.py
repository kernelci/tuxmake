from tuxmake.wrapper import Wrapper


class TestNone:
    def test_basics(self):
        none = Wrapper("none")
        assert none.environment == {}
        assert none.wrap({}) == {}


class Test_ccache:
    def test_environment(self, monkeypatch, home):
        monkeypatch.delenv("CCACHE_DIR", raising=False)
        ccache = Wrapper("ccache")
        assert ccache.environment["CCACHE_DIR"] == f"{home}/.ccache"

    def test_environment_exists(self, monkeypatch):
        monkeypatch.setenv("CCACHE_DIR", "/ccache")
        ccache = Wrapper("ccache")
        assert ccache.environment["CCACHE_DIR"] == "/ccache"

    def test_prepare(self, home, mocker):
        build = mocker.MagicMock()
        Wrapper("ccache").prepare(build)
        assert (home / ".ccache").exists()
        build.run_cmd.assert_called_with(["ccache", "--zero-stats"], stdout=mocker.ANY)


class Test_sccache:
    def test_environment(self, monkeypatch, home):
        monkeypatch.delenv("SCCACHE_DIR", raising=False)
        sccache = Wrapper("sccache")
        assert sccache.environment["SCCACHE_DIR"] == f"{home}/.cache/sccache"
        assert sccache.path is None

    def test_with_full_path(self, monkeypatch, home):
        wrapper = Wrapper("/path/to/sccache")
        assert wrapper.name == "sccache"
        assert wrapper.path == "/path/to/sccache"
