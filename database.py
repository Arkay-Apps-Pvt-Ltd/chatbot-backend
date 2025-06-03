from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import config

DATABASE_URL = (
    "mysql+pymysql://"
    + config["db_user"]
    + ":"
    + config["db_pass"]
    + "@"
    + config["db_host"]
    + "/"
    + config["db_name"]
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=True)

Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()