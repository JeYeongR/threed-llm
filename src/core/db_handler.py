import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import DBCompanyPost, get_db
from src.models.dto import CompanyPost

logger = logging.getLogger(__name__)


def save_to_rds(posts: List[CompanyPost]) -> Tuple[int, int]:
    """주어진 CompanyPost 목록을 단일 트랜잭션으로 RDS에 저장합니다."""
    if not posts:
        return 0, 0

    saved_count = 0
    error_count = 0

    try:
        with _db_session_manager() as db:
            logger.info(f"RDS에 {len(posts)}개 포스트 저장을 시도합니다.")
            for post_dto in posts:
                db_post = DBCompanyPost(
                    title=post_dto.title,
                    content=post_dto.summary,
                    field=post_dto.field,
                    company=post_dto.company,
                    source_url=post_dto.url,
                    thumbnail_image_url=post_dto.thumbnail_url,
                    published_at=post_dto.published_at,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    view_count=0,
                )
                db.add(db_post)

            saved_count = len(posts)

    except IntegrityError as e:
        logger.error(
            f"무결성 제약 조건 위반. 중복된 URL이 있을 수 있습니다. 전체 배치가 롤백됩니다. 오류: {e}",
            exc_info=True,
        )
        error_count = len(posts)
    except Exception as e:
        logger.error(
            f"데이터베이스 저장 중 오류 발생. 전체 배치가 롤백됩니다. 오류: {e}",
            exc_info=True,
        )
        error_count = len(posts)

    final_saved_count = saved_count - error_count
    if error_count == 0:
        logger.info(f"RDS 저장 완료: {final_saved_count}개 성공.")

    return final_saved_count, error_count


@contextmanager
def _db_session_manager() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    db_gen = get_db()
    db = next(db_gen, None)
    if db is None:
        logger.error("데이터베이스 세션을 가져올 수 없습니다.")
        try:
            next(db_gen)
        except StopIteration:
            pass
        raise IOError("Failed to get DB session")

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
