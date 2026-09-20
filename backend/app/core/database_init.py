from app.core.database import engine
from app.models.database import Base


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)