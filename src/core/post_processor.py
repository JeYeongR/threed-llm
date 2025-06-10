import logging
from typing import List
from urllib.parse import unquote, urlparse, urlunparse

import requests

from src.database import DBCompanyPost, get_db, init_db
from src.models.dto import CompanyPost, CrawledContentDto
from src.models.enums import Company, Field
from src.services.summarizer import summarize_content
from src.utils.s3_uploader import s3_uploader

logger = logging.getLogger(__name__)


def process_posts(crawled_posts: List[CrawledContentDto]) -> List[CompanyPost]:
    """크롤링된 포스트를 처리하고 요약을 추가합니다."""
    processed_posts = []
    db_session = _get_db_session()

    for i, crawled in enumerate(crawled_posts, 1):
        try:
            logger.info(f"[{i}/{len(crawled_posts)}] '{crawled.title}' 처리 중...")

            if _is_duplicate_post(db_session, crawled):
                logger.info(
                    f"  - 이미 저장된 포스트: {crawled.title} (요약 및 저장 건너뜀)"
                )
                continue

            logger.info(f"  - 콘텐츠 요약 중...")
            summary_result = summarize_content(crawled.content)

            company_name = _get_company_name(crawled.source_name)
            company = _get_company_enum(company_name)

            logger.info(f"  - 썸네일 처리 중...")
            thumbnail_url = _process_thumbnail(crawled.thumbnail_url, company_name)

            current_post_raw_url = crawled.url
            if (
                isinstance(current_post_raw_url, dict)
                and "href" in current_post_raw_url
            ):
                current_post_raw_url = current_post_raw_url["href"]

            if not isinstance(current_post_raw_url, str):
                logger.error(
                    f"URL for DTO is not a string after dict check: {type(current_post_raw_url)}, value: {current_post_raw_url}. Skipping post."
                )
                continue

            normalized_url_for_dto = _normalize_url(current_post_raw_url)
            if not normalized_url_for_dto:
                logger.error(
                    f"URL normalization resulted in empty string for {current_post_raw_url}. Skipping post."
                )
                continue

            processed_post = CompanyPost(
                title=crawled.title,
                summary=summary_result["summary"],
                thumbnail_url=thumbnail_url,
                field=Field(summary_result["field"]),
                published_at=crawled.published_at,
                company=company,
                url=normalized_url_for_dto,  # 정규화된 URL 저장
            )

            processed_posts.append(processed_post)
            logger.info(f"  - 포스트 처리 완료: {crawled.title}")

        except Exception as e:
            logger.error(f"포스트 처리 중 오류 발생: {str(e)}")

    _close_db_session(db_session)
    return processed_posts


def _get_db_session():
    """데이터베이스 세션을 가져옵니다."""
    init_db()
    db_gen = get_db()
    db = next(db_gen, None)

    if db is None:
        logger.error(
            "데이터베이스 세션을 가져올 수 없습니다. 중복 검사 없이 처리합니다."
        )

    return (db, db_gen)


def _close_db_session(db_session):
    """데이터베이스 세션을 닫습니다."""
    if db_session:
        try:
            next(db_session[1])
        except StopIteration:
            pass


def _is_duplicate_post(db_session, crawled):
    """포스트가 이미 데이터베이스에 존재하는지 확인합니다."""
    if not db_session or not db_session[0]:
        return False

    raw_url = crawled.url
    # feedparser가 URL을 dict 형태로 반환하는 경우 처리
    if isinstance(raw_url, dict) and "href" in raw_url:
        raw_url = raw_url["href"]

    normalized_url = _normalize_url(raw_url)  # 최상위 레벨의 _normalize_url 호출
    logger.info(f"  - 중복 확인 (정규화된 URL): {normalized_url}")

    exists = (
        db_session[0]
        .query(DBCompanyPost)
        .filter(DBCompanyPost.source_url == normalized_url)
        .first()
    )
    return exists is not None


def _normalize_url(url: str) -> str:
    """URL에서 쿼리 파라미터, 프래그먼트, 불필요한 경로 요소를 제거하여 정규화합니다."""
    # feedparser가 URL을 dict 형태로 반환하는 경우 처리 (방어적 코딩)
    if isinstance(url, dict) and "href" in url:
        url = url["href"]

    if not isinstance(url, str):
        # logger.warning(f"정규화할 수 없는 URL 타입: {type(url)}, 값: {url}")
        # URL이 문자열이 아니면, 문자열로 변환 시도 또는 원본 반환 (혹은 오류 발생)
        # 여기서는 일단 문자열로 변환 시도 후 진행
        try:
            url = str(url)
        except Exception:
            # logger.error(f"URL을 문자열로 변환 실패: {url}")
            return url  # 변환 실패 시 원본 반환

    parsed = urlparse(url)
    # 경로 디코딩 및 정리
    path = unquote(parsed.path)
    path = path.lower()  # 경로를 소문자로 변환
    path = path.rstrip("/")

    # 경로(path)에 '?'나 '#'이 잘못 포함된 경우 명시적으로 제거
    if "?" in path:
        path = path.split("?", 1)[0]
    if "#" in path:
        path = path.split("#", 1)[0]

    # params, query, fragment는 비워두고 재구성
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _get_company_name(source_name):
    """소스 이름에서 회사 이름을 찾습니다."""
    from src.config.blog_config import BLOG_CONFIGS

    for config in BLOG_CONFIGS:
        if config["name"] == source_name:
            return config["company"]
    return None


def _process_thumbnail(thumbnail_url, company_name):
    """썸네일을 다운로드하고 S3에 업로드합니다."""
    if not thumbnail_url:
        return None

    try:
        logger.info(f"    - 썸네일 다운로드 중: {thumbnail_url}")
        response = requests.get(thumbnail_url, timeout=10)
        response.raise_for_status()

        logger.info("    - S3에 썸네일 업로드 중...")
        s3_url = s3_uploader.upload_image(
            response.content,
            company_name=company_name.lower() if company_name else None,
            original_filename=(
                thumbnail_url.split("/")[-1] if "/" in thumbnail_url else None
            ),
        )

        if s3_url:
            logger.info(f"    - S3 업로드 성공: {s3_url}")
            return s3_url
        else:
            logger.warning("    - S3 업로드 실패, 원본 URL 사용")
            return thumbnail_url
    except Exception as e:
        logger.error(f"    - 썸네일 처리 중 오류 발생: {str(e)}")
        return thumbnail_url


def _get_company_enum(company_name):
    """회사 이름에서 Company enum을 가져옵니다."""
    try:
        return Company[company_name] if company_name else Company.ETC
    except KeyError:
        return Company.ETC
