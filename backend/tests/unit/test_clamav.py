import pytest

from app.integrations import clamav


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        ([b"stream: ", b"OK\0"], None),
        ([b"stream: test-signature FOUND\0"], "scan_rejected"),
        ([b"stream: OK", b""], "scan_unavailable"),
        ([b"INSTREAM size limit exceeded. ERROR\0"], "scan_unavailable"),
        ([b"stream: OK\0unexpected"], "scan_unavailable"),
    ],
)
def test_clamav_accepts_only_a_complete_clean_reply(monkeypatch, parts, expected):
    outgoing = []
    incoming = iter(parts)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, seconds):
            assert 0 < seconds <= 8

        def sendall(self, value):
            outgoing.append(value)

        def recv(self, maximum):
            assert 0 < maximum <= 512
            return next(incoming)

    def connect(address, timeout):
        assert address == ("127.0.0.1", 3310) and timeout == 3
        return Connection()

    monkeypatch.setattr(clamav.socket, "create_connection", connect)
    assert clamav.scan(b"test", 3310) == expected
    assert b"".join(outgoing) == b"zINSTREAM\0\0\0\0\x04test\0\0\0\0"
