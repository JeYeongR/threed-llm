import logging
import re
from typing import Optional

import requests
from PIL import Image

from src.services.crawler_constants import DEFAULT_HEADERS, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def extract_image_url_from_html(html: str) -> str:
    """웹 페이지 HTML에서 첫 번째 이미지 URL을 추출합니다.

    Args:
        html: 추출할 HTML 문자열

    Returns:
        추출된 이미지 URL 또는 빈 문자열
    """
    if not html:
        return ""

    img_match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', html, re.IGNORECASE)
    if img_match:
        return img_match.group(1)
    return ""


def extract_thumbnail_from_webpage(
    session: requests.Session, url: str
) -> Optional[str]:
    """웹 페이지에서 썸네일 이미지 URL을 추출합니다.

    Args:
        session: 요청에 사용할 세션 객체
        url: 웹 페이지 URL

    Returns:
        추출된 썸네일 URL 또는 None
    """
    if not url:
        return None

    try:
        logger.info(f"원본 링크에서 썸네일 추출 시도: {url}")
        response = session.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        og_image_match = re.search(
            r'<meta\s+property=[\'"]og:image[\'"]\s+content=[\'"]([^\'"]+)[\'"]',
            response.text,
            re.IGNORECASE,
        )

        if og_image_match:
            thumbnail_url = og_image_match.group(1)
            logger.info(f"Open Graph 태그에서 썸네일 찾음: {thumbnail_url}")
            return normalize_thumbnail_url(thumbnail_url, url)

        img_match = re.search(
            r'<div\s+class=[\'"]thumbnail[\'"][^>]*>\s*<img[^>]+src=[\'"]([^\'"]+)[\'"]',
            response.text,
            re.IGNORECASE,
        )
        if img_match:
            thumbnail_url = img_match.group(1)
            logger.info(f"썸네일 클래스에서 이미지 찾음: {thumbnail_url}")
            return normalize_thumbnail_url(thumbnail_url, url)

        img_match = re.search(
            r'<img[^>]+src=[\'"]([^\'"]+)[\'"]',
            response.text,
            re.IGNORECASE,
        )
        if img_match:
            thumbnail_url = img_match.group(1)
            logger.info(f"첫 번째 이미지 태그에서 썸네일 찾음: {thumbnail_url}")
            return normalize_thumbnail_url(thumbnail_url, url)

    except Exception as e:
        logger.error(f"원본 링크에서 썸네일 추출 중 오류: {str(e)}")

    return None


def normalize_thumbnail_url(thumbnail_url: str, base_url: str) -> str:
    """썸네일 URL을 절대 경로로 정규화합니다.

    Args:
        thumbnail_url: 정규화할 썸네일 URL
        base_url: 기본 URL (상대 경로일 경우 사용)

    Returns:
        정규화된 절대 경로 URL
    """
    if not thumbnail_url:
        return ""

    if thumbnail_url.startswith("http://") or thumbnail_url.startswith("https://"):
        return thumbnail_url

    if thumbnail_url.startswith("/"):
        base_url = "/".join(base_url.split("/")[:3])
        return base_url + thumbnail_url
    else:
        return base_url.rstrip("/") + "/" + thumbnail_url


def extract_text_from_html(html: str) -> str:
    """HTML에서 텍스트만 추출합니다.

    Args:
        html: 추출할 HTML 문자열

    Returns:
        추출된 텍스트
    """
    if not html:
        return ""

    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text
