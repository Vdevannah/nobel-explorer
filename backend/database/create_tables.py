import backend.models  # noqa: F401 - registers model metadata

from backend.database.connection import Base, engine


def create_tables() -> None:
    """Create all database tables defined by the application models."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")
