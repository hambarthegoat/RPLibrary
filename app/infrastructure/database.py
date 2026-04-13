from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings

engine = create_engine(settings.database_url)

def get_db():
    with Session(engine) as session:
        yield session

