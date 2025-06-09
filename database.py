from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv
from models import Company, Field
from typing import Generator
from db_tunnel import db_tunnel

load_dotenv()

Base = declarative_base()
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
        
        global engine
        engine = create_engine(
            DATABASE_URL,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        
        SessionLocal = get_session_factory(engine)
        
        print("데이터베이스 연결이 성공적으로 설정되었습니다.")
        print(f"SessionLocal: {SessionLocal}")
        
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        if engine is not None:
            engine.dispose()
            engine = None
        raise

class DBPost(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    thumbnail_image_url = Column(String(255), nullable=True)
    field = Column(Enum(Field), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    view_count = Column(Integer, nullable=False, default=0)
    post_type = Column(String(31), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_on': post_type,
        'polymorphic_identity': 'POST'
    }

class DBCompanyPost(DBPost):
    __tablename__ = "company_posts"
    
    id = Column(Integer, ForeignKey("posts.id"), primary_key=True)
    source_url = Column(String(255), nullable=True)
    company = Column(Enum(Company), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'COMPANY'
    }

def get_db() -> Generator:
    """데이터베이스 세션 의존성 주입"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
