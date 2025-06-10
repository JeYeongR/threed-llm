import logging
from typing import Generator, List, Optional, Tuple
from urllib.parse import unquote, urlparse, urlunparse

import requests
from sqlalchemy.orm import Session

from src.database import DBCompanyPost, get_db, init_db
from src.models.dto import CompanyPost, CrawledContentDto
from src.models.enums import Field
from src.services.summarizer import summarize_content
from src.utils.s3_uploader import s3_uploader

logger = logging.getLogger(__name__)


def process_posts(crawled_posts: List[CrawledContentDto]) -> List[CompanyPost]:
    """크롤링된 포스트를 처리하고 요약을 추가합니다."""
    processed_posts: List[CompanyPost] = []
    db_session_info = _get_db_session()
    db = db_session_info[0] if db_session_info else None

    for i, crawled in enumerate(crawled_posts, 1):
        try:
            logger.info(f"[{i}/{len(crawled_posts)}] '{crawled.title}' 처리 중...")

            if _is_duplicate_post(db, crawled):
                logger.info(
                    f"  - 이미 저장된 포스트: {crawled.title} (요약 및 저장 건너뜀)"
                )
                continue

            logger.info(f"  - 콘텐츠 요약 중...")
            summary_result = summarize_content(crawled.content)

            company = crawled.company

            logger.info(f"  - 썸네일 처리 중...")
            thumbnail_s3_url = _process_thumbnail(
                crawled.thumbnail_url, crawled.company.name.lower()
            )

            normalized_url = _normalize_url(crawled.url)
            if not normalized_url:
                logger.error(
                    f"URL 정규화 실패: {crawled.url}. 포스트를 건너<0xEB><01><0x81>니다."
                )
                continue

            processed_post = CompanyPost(
                title=crawled.title,
                summary=summary_result["summary"],
                thumbnail_url=thumbnail_s3_url,
                field=Field(summary_result["field"]),
                published_at=crawled.published_at,
                company=crawled.company,
                url=normalized_url,
            )

            processed_posts.append(processed_post)
            logger.info(f"  - 포스트 처리 완료: {crawled.title}")

        except Exception as e:
            logger.error(
                f"포스트 '{crawled.title}' 처리 중 오류 발생: {e}", exc_info=True
            )

    _close_db_session(db_session_info)
    return processed_posts


def _get_db_session() -> Optional[Tuple[Session, Generator[Session, None, None]]]:
    """데이터베이스 세션을 가져옵니다."""
    init_db()
    db_gen = get_db()
    db = next(db_gen, None)

    if db is None:
        logger.error(
            "데이터베이스 세션을 가져올 수 없습니다. 중복 검사 없이 처리합니다."
        )
        try:
            next(db_gen)
        except StopIteration:
            pass
        return None
    return db, db_gen


def _close_db_session(
    db_session_info: Optional[Tuple[Session, Generator[Session, None, None]]]
) -> None:
    """데이터베이스 세션을 닫습니다."""
    if db_session_info and db_session_info[1]:
        try:
            next(db_session_info[1])
        except StopIteration:
            pass


def _is_duplicate_post(db: Optional[Session], crawled: CrawledContentDto) -> bool:
    """포스트가 이미 데이터베이스에 존재하는지 확인합니다."""
    if not db:
        return False

    normalized_url = _normalize_url(crawled.url)
    if not normalized_url:
        logger.warning(
            f"중복 검사를 위한 URL 정규화 실패: {crawled.url}. 중복으로 간주하지 않음."
        )
        return False

    logger.info(f"  - 중복 확인 (정규화된 URL): {normalized_url}")

    exists = (
        db.query(DBCompanyPost)
        .filter(DBCompanyPost.source_url == normalized_url)
        .first()
    )
    return exists is not None


def _normalize_url(url: any) -> str:
    """URL에서 쿼리 파라미터, 프래그먼트, 불필요한 경로 요소를 제거하여 정규화합니다."""
    if isinstance(url, dict) and "href" in url:
        url_str = url["href"]
    elif isinstance(url, str):
        url_str = url
    else:
        try:
            url_str = str(url)
        except Exception:
            logger.error(f"URL을 문자열로 변환 실패: {url}, 타입: {type(url)}")
            return ""

    try:
        parsed = urlparse(url_str)
        path = unquote(parsed.path)
        path = path.lower()
        path = path.rstrip("/")

        if "?" in path:
            path = path.split("?", 1)[0]
        if "#" in path:
            path = path.split("#", 1)[0]

        return urlunparse((parsed.scheme, parsed.netloc.lower(), path, "", "", ""))
    except Exception as e:
        logger.error(f"URL 정규화 중 오류 발생: {url_str} - {e}", exc_info=True)
        return ""


def _process_thumbnail(
    thumbnail_url: Optional[str], company_name: Optional[str]
) -> Optional[str]:
    """썸네일을 다운로드하고 S3에 업로드합니다."""
    if not thumbnail_url:
        return None

    try:
        logger.info(f"    - 썸네일 다운로드 중: {thumbnail_url}")
        response = requests.get(thumbnail_url, timeout=10)
        response.raise_for_status()

        file_content = response.content
        original_filename = (
            thumbnail_url.split("/")[-1] if "/" in thumbnail_url else "thumbnail"
        )

        if "." in original_filename:
            filename_parts = original_filename.split(".")
            extension_candidate = filename_parts[-1].split("?")[0].split("#")[0]
            if len(extension_candidate) <= 5:
                original_filename = (
                    ".".join(filename_parts[:-1]) + "." + extension_candidate
                )
            else:
                original_filename = ".".join(filename_parts[:-1])

        logger.info("    - S3에 썸네일 업로드 중...")
        s3_url = s3_uploader.upload_image(
            file_content,
            company_name=company_name.lower() if company_name else "etc",
            original_filename=original_filename,
        )

        if s3_url:
            logger.info(f"    - S3 업로드 성공: {s3_url}")
            return s3_url
        else:
            logger.warning("    - S3 업로드 실패, 원본 URL 사용 시도")
            return thumbnail_url
    except requests.exceptions.RequestException as e:
        logger.error(
            f"    - 썸네일 다운로드 중 오류 발생 (RequestException): {thumbnail_url} - {e}",
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            f"    - 썸네일 처리 중 예기치 않은 오류 발생: {thumbnail_url} - {e}",
            exc_info=True,
        )

    return thumbnail_url
