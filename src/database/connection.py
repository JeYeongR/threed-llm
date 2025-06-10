"""
데이터베이스 연결 및 세션 관리를 담당하는 모듈입니다.

이 모듈은 SSH 터널을 설정하여 데이터베이스에 안전하게 연결하고,
SQLAlchemy 엔진 및 세션 팩토리를 초기화합니다. 애플리케이션 전역에서
사용될 데이터베이스 세션을 제공하는 함수(`get_db`)를 포함합니다.
"""

import logging
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.utils.ssh_tunnel import db_tunnel

logger = logging.getLogger(__name__)

engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker[Session]] = None


def get_session_factory(bind: Engine) -> sessionmaker[Session]:
    """
    주어진 SQLAlchemy 엔진에 바인딩된 세션 팩토리를 생성합니다.

    Args:
        bind: SQLAlchemy 엔진 객체.

    Returns:
        autocommit=False, autoflush=False로 설정된 세션 팩토리.
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=bind)


def init_db() -> None:
    """
    데이터베이스 연결을 초기화합니다.

    SSH 터널을 시작하고, 연결 파라미터를 가져와 SQLAlchemy 엔진을 생성합니다.
    그 다음, 세션 팩토리(SessionLocal)를 설정합니다.
    이 함수는 애플리케이션 시작 시 한 번만 호출되어야 합니다.
    이미 초기화된 경우 아무 작업도 수행하지 않습니다.

    Raises:
        Exception: SSH 터널 시작 또는 데이터베이스 연결 설정 중 오류 발생 시.
    """
    global engine, SessionLocal

    if SessionLocal is not None:
        logger.info("데이터베이스 연결이 이미 설정되어 있습니다.")
        return

    try:
        logger.info("SSH 터널을 시작합니다...")
        if not db_tunnel.start():
            raise Exception("SSH 터널 시작에 실패했습니다.")
        logger.info("SSH 터널이 성공적으로 시작되었습니다.")

        conn_params = db_tunnel.get_connection_params()
        logger.debug(
            f"DB 연결 파라미터: 호스트-{conn_params['host']}, 포트-{conn_params['port']}, DB명-{conn_params['db']}"
        )

        DATABASE_URL = (
            f"mysql+pymysql://{conn_params['user']}:{conn_params['password']}@"
            f"{conn_params['host']}:{conn_params['port']}/{conn_params['db']}?charset=utf8mb4"
        )

        engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)

        with engine.connect() as connection:
            logger.info("데이터베이스 엔진 연결 테스트 성공.")

        SessionLocal = get_session_factory(engine)

        logger.info("데이터베이스 연결 및 세션 팩토리가 성공적으로 설정되었습니다.")

    except Exception as e:
        logger.error(
            f"데이터베이스 초기화 중 심각한 오류 발생: {str(e)}", exc_info=True
        )
        if engine is not None:
            engine.dispose()
            engine = None
        SessionLocal = None
        raise


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 제너레이터를 제공합니다.

    FastAPI 등의 의존성 주입 시스템에서 사용하기 적합한 형태로,
    세션을 생성하고 사용 후 자동으로 닫습니다.

    Yields:
        데이터베이스 세션 객체 (Session).

    Raises:
        Exception: SessionLocal이 초기화되지 않은 경우 AttributeError 발생 가능.
                   (init_db()가 먼저 호출되어야 함)
    """
    if SessionLocal is None:
        logger.critical(
            "SessionLocal이 초기화되지 않았습니다. init_db()를 먼저 호출해야 합니다."
        )
        raise RuntimeError("데이터베이스 세션 팩토리가 초기화되지 않았습니다.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
