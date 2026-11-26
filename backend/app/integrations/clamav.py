"""Screen PDF bytes through a private, loopback ClamAV daemon."""

import socket
from time import monotonic


def scan(original: bytes, port: int | None) -> str | None:
    if port is None:
        return "scan_unavailable"
    deadline = monotonic() + 8
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
            for part in (b"zINSTREAM\0" + len(original).to_bytes(4, "big"), original, b"\0" * 4):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return "scan_unavailable"
                connection.settimeout(remaining)
                connection.sendall(part)
            response = bytearray()
            while b"\0" not in response and len(response) < 512:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    return "scan_unavailable"
                connection.settimeout(remaining)
                data = connection.recv(512 - len(response))
                if not data:
                    break
                response.extend(data)
    except OSError:
        return "scan_unavailable"
    if response == b"stream: OK\0":
        return None
    if response.startswith(b"stream: ") and response.endswith(b" FOUND\0"):
        return "scan_rejected"
    return "scan_unavailable"
