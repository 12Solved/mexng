from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from mailextractor.backend.config import config

engine = create_engine(config.DATABASE_URL)
Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
