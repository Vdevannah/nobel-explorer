from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.application import Application


def get_by_id(
    db: Session,
    application_id: int
) -> Application | None:
    statement = select(Application).where(
        Application.application_id == application_id
    )
    return db.scalar(statement)


def get_by_discovery(
    db: Session,
    discovery_id: int
) -> list[Application]:
    statement = select(Application).where(
        Application.discovery_id == discovery_id
    )
    return list(db.scalars(statement).all())


def create(
    db: Session,
    application: Application
) -> Application:
    db.add(application)
    db.flush()
    db.refresh(application)

    return application


def update(
    db: Session,
    application: Application,
    title: str,
    description: str | None,
    source_name: str | None,
    source_url: str | None
) -> Application:
    application.title = title
    application.description = description
    application.source_name = source_name
    application.source_url = source_url

    db.flush()
    db.refresh(application)

    return application


def delete(
    db: Session,
    application: Application
) -> None:
    db.delete(application)
    db.flush()