import tuxmake.__main__
import tuxmake.cli


def test_tuxmake_main_is_cli_main():
    assert tuxmake.__main__.main is tuxmake.cli.main


def test_calls_main_when___name___is___main__(monkeypatch, mocker):
    main = mocker.patch("tuxmake.__main__.main")
    monkeypatch.setattr(tuxmake.__main__, "__name__", "__main__")
    tuxmake.__main__.run()
    main.assert_called()
