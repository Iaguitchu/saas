from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.settings import Settings

settings = Settings()



engine = create_engine(settings.DB_URL, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
