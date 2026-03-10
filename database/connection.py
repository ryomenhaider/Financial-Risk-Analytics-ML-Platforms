import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config.logging_config import get_logger
from config.settings import DB_URL, LOG_LEVEL

logger = get_logger(__name__)

# FIX: guard against empty DB_URL (settings.py now returns "" instead of raising)
if not DB_URL:
    logger.error(
        "DB_URL is not set. Database features will be unavailable. "
        "Set the DB_URL environment variable in Koyeb."
    )
    engine = None
    Session_local = None
else:
    engine = create_engine(
        DB_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    Session_local = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )


# FIX: every router uses `with get_session() as session:` which requires a
# context manager. The old get_session() returned a plain Session object,
# causing `AttributeError: __enter__` on every single API request.
@contextmanager
def get_session():
    if Session_local is None:
        raise RuntimeError(
            "Database is not configured. Set the DB_URL environment variable."
        )
    session: Session = Session_local()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_connection() -> bool:
    if Session_local is None:
        logger.error("DB_URL not configured — skipping connection test")
        return False
    try:
        with get_session() as session:
            result = session.execute(text("SELECT 1"))
            value = result.scalar()
            logger.info(f"DB connection OK — SELECT 1 returned {value}")
            return True
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()