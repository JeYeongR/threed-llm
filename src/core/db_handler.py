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


def delete_posts_by_company(company_name: str) -> int:
    """
    Deletes all posts for a given company from the database.
    Returns the number of deleted posts.
    """
    deleted_count = 0
    init_db()  # 데이터베이스 초기화 보장
    # get_db()를 통해 세션을 얻을 때 이미 초기화가 보장된다면 중복 호출은 불필요.

    db_gen = get_db()
    db = next(db_gen, None)

    if db is None:
        logger.error(
            "데이터베이스 세션을 가져올 수 없습니다. 삭제 작업을 진행할 수 없습니다."
        )
        return 0

    try:
        logger.info(f"{company_name} 회사의 포스트를 삭제합니다...")
        # DBCompanyPost.company 필드가 BlogType enum의 name (문자열)을 저장한다고 가정합니다.
        posts_to_delete = (
            db.query(DBCompanyPost).filter(DBCompanyPost.company == company_name).all()
        )

        if not posts_to_delete:
            logger.info(
                f"{company_name} 회사에 해당하는 포스트가 데이터베이스에 없습니다."
            )
            return 0

        num_to_delete = len(posts_to_delete)

        for post in posts_to_delete:
            db.delete(post)

        db.commit()
        deleted_count = num_to_delete
        logger.info(
            f"{company_name} 회사 포스트 {deleted_count}개가 성공적으로 삭제되었습니다."
        )

    except Exception as e:
        db.rollback()
        logger.error(f"{company_name} 회사 포스트 삭제 중 오류 발생: {str(e)}")
        # deleted_count는 이미 0으로 초기화되어 있으므로 실패 시 0 반환
    finally:
        try:
            next(db_gen)  # Close session
        except StopIteration:
            pass

    return deleted_count
