from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from typing import Generator
import logging

from src.database.models import Base
from src.utils.ssh_tunnel import db_tunnel

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None

def get_session_factory(bind):
    """세션 팩토리 생성"""
    return sessionmaker(autocommit=False, autoflush=False, bind=bind)

def init_db():
    """데이터베이스 초기화"""
    global engine, SessionLocal
    
    if SessionLocal is not None:
        return
        
    try:
        if not db_tunnel.start():
            raise Exception("SSH 터널 시작 실패")
        
        conn_params = db_tunnel.get_connection_params()
        
        DATABASE_URL = (
            f"mysql+pymysql://{conn_params['user']}:{conn_params['password']}@"
            f"{conn_params['host']}:{conn_params['port']}/{conn_params['db']}?charset=utf8mb4"
        )
        
        engine = create_engine(
            DATABASE_URL,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        SessionLocal = get_session_factory(engine)
        
        logger.info("데이터베이스 연결이 성공적으로 설정되었습니다.")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        if engine is not None:
            engine.dispose()
            engine = None
        raise

def get_db() -> Generator:
    """데이터베이스 세션 의존성 주입"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
