def test_import():
    from pyheartradio import IHeartRadio


def test_version():
    from pyheartradio.version import __version__
    assert __version__


def test_instantiate():
    from pyheartradio import IHeartRadio
    client = IHeartRadio()
    assert client.timeout == 10
    assert client.session is not None
