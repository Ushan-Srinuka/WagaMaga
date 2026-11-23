"""Check readiness, process queued synthetic PDFs and refresh opted-in farm forecasts."""

import argparse
import logging
import signal
from threading import Event

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.db.database import Database
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.knowledge.processing import process_one
from app.modules.notifications import models as notification_models  # noqa: F401
from app.modules.weather import scheduled

logger = logging.getLogger("wagamaga.worker")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Check DB/schema once and exit")
    args = parser.parse_args()
    settings = Settings()
    database = Database(settings)
    stop = Event()

    def request_stop(signum: int, frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        while not stop.is_set():
            ready = database.check_ready()
            if args.once:
                logger.info("Worker database=%s", ready.status)
                return 0 if ready.status == "ready" else 1
            if ready.status == "ready" and database.engine is not None:
                if settings.app_env != "production":
                    try:
                        process_one(database.engine)
                    except SQLAlchemyError, OSError, ValueError:
                        logger.warning("PDF job could not be completed. The worker will retry.")
                try:
                    scheduled.process_one(database.engine, settings)
                except SQLAlchemyError, OSError, ValueError:
                    logger.warning("Scheduled weather could not be saved. The worker will retry.")
            stop.wait(2)
    finally:
        database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
