import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config.logging_config import get_logger
from config.settings import DB_URL, LOG_LEVEL

logger = get_logger(__name__)

engine = create_engine(
    DB_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)

Session_local=sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

def get_session() -> Session:
    return Session_local()

def test_connection() -> None:
        
        session = get_session()
        try:
            result = session.execute(text("SELECT 1"))
            value = result.scalar()
            print(f'query result: {value}')
            logger.info('The DB has connected')
            return True
        except Exception as e:
            logger.error(f"DB Connection failed: {e}")
            return False
            raise
            
        finally:
             session.close()

if __name__ == "__main__":
    test_connection()