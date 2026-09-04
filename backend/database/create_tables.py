import backend.models  # noqa: F401 - registers model metadata

from backend.database.connection import Base, engine


def create_tables() -> None:
    """Create tables for educational/reference use only.

    Alembic migrations are authoritative for development and production
    schema creation and evolution. Use ``alembic upgrade head`` for normal
    database setup.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")
