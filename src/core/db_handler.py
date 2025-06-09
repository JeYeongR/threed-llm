import logging
from datetime import datetime
from typing import List, Tuple

from sqlalchemy.exc import IntegrityError

from src.database import DBCompanyPost, get_db, init_db
from src.models.dto import CompanyPost

logger = logging.getLogger(__name__)


def save_to_rds(posts: List[CompanyPost]) -> Tuple[int, int]:
    saved_count = 0
    error_count = 0

    init_db()

    db_gen = get_db()
    db = next(db_gen, None)

    if db is None:
        logger.error("데이터베이스 세션을 가져올 수 없습니다.")
        return 0, len(posts)

    try:
        for post in posts:
            try:
                try:
                    url_to_check = post.url
                    if isinstance(url_to_check, dict) and "href" in url_to_check:
                        url_to_check = url_to_check["href"]

                    logger.debug(f"URL 체크: {url_to_check}")
                    exists = (
                        db.query(DBCompanyPost)
                        .filter(DBCompanyPost.source_url == url_to_check)
                        .first()
                    )
                    if exists:
                        logger.info(f"이미 존재하는 포스트: {post.title}")
                        error_count += 1
                        continue
                except Exception as e:
                    logger.error(f"URL 체크 오류: {str(e)}")
                    error_count += 1
                    continue

                url_to_save = post.url
                if isinstance(url_to_save, dict) and "href" in url_to_save:
                    url_to_save = url_to_save["href"]

                summary_content = None
                if hasattr(post, "summary") and post.summary:
                    summary_content = post.summary

                db_post = DBCompanyPost(
                    title=post.title,
                    content=summary_content,
                    field=post.field,
                    company=post.company,
                    source_url=url_to_save,
                    thumbnail_image_url=post.thumbnail_url,
                    published_at=post.published_at,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    view_count=0,
                )

                db.add(db_post)
                db.commit()
                saved_count += 1
                logger.info(f"RDS 저장 성공: {post.title}")

            except IntegrityError as e:
                db.rollback()
                logger.error(f"무결성 오류 ({post.title}): {str(e)}")
                error_count += 1

    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 오류: {str(e)}")
        error_count = len(posts) - saved_count
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    return saved_count, error_count
