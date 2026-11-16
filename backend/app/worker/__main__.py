"""Heartbeat/check entry point, not an implementation of durable job processing."""

import argparse
import logging
import signal
from threading import Event

from app.core.config import Settings
from app.db.database import Database

logger = logging.getLogger("wagamaga.worker")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Check DB/schema once and exit")
    args = parser.parse_args()
    database = Database(Settings())
    stop = Event()

    def request_stop(signum: int, frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        while not stop.is_set():
            ready = database.check_ready()
            logger.info("Worker foundation: database=%s; no job handlers configured", ready.status)
            if args.once:
                return 0 if ready.status == "ready" else 1
            stop.wait(15)
    finally:
        database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
