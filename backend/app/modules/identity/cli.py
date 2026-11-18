"""Restricted local first-administrator setup; no credentials in arguments or logs."""

from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.modules.identity.schemas import Register
from app.modules.identity.security import IdentityError
from app.modules.identity.service import bootstrap_admin


def main() -> int:
    settings = Settings()
    if settings.migration_database_url is None:
        print("Configure MIGRATION_DATABASE_URL before initial administrator setup.")
        return 1
    name = input("Administrator display name: ")
    email = input("Administrator email: ")
    password = getpass("Password (8-128 characters; include a letter, number and symbol): ")
    if getpass("Confirm password: ") != password:
        print("Passwords do not match.")
        return 1
    engine = create_engine(settings.migration_database_url.get_secret_value(), hide_parameters=True)
    try:
        data = Register(display_name=name, email=email, password=password)
        with Session(engine) as db, db.begin():
            bootstrap_admin(db, data)
    except ValidationError:
        print("Check the name, email and password requirements; no account created.")
        return 1
    except IdentityError as error:
        print(error.message)
        return 1
    except SQLAlchemyError:
        print("Database unavailable or migration missing. No administrator was created.")
        return 1
    finally:
        engine.dispose()
    print("Initial administrator created. Sign in through the application.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
