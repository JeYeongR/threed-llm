import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests import Session as RequestsSession

from src.services.crawler_constants import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def extract_thumbnail_from_webpage(session: RequestsSession, url: str) -> Optional[str]:
    """
    웹페이지에서 썸네일 URL을 추출합니다.

    Open Graph(og:image), Twitter Card(twitter:image) 등 표준 메타 태그를
    우선적으로 확인하고, 없을 경우 HTML 본문의 첫 번째 이미지를 대안으로 사용합니다.

    Args:
        session: HTTP 요청에 사용할 requests.Session 객체.
        url: 썸네일을 추출할 웹페이지의 URL.

    Returns:
        추출된 썸네일의 절대 URL. 찾지 못한 경우 None.
    """
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
        soup = BeautifulSoup(html_content, "lxml")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            logger.debug(f"'{url}'에서 'og:image' 메타 태그로 썸네일 찾음.")
            return urljoin(url, og_image["content"])

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            logger.debug(f"'{url}'에서 'twitter:image' 메타 태그로 썸네일 찾음.")
            return urljoin(url, twitter_image["content"])

        image_src_link = soup.find("link", rel="image_src")
        if image_src_link and image_src_link.get("href"):
            logger.debug(f"'{url}'에서 'link[rel=image_src]' 태그로 썸네일 찾음.")
            return urljoin(url, image_src_link["href"])

        logger.info(
            f"'{url}'에서 메타 태그 썸네일을 찾지 못해 본문 이미지 검색을 시도합니다."
        )
        body_image_url = _extract_image_url_from_html(html_content, url)
        if body_image_url:
            logger.debug(f"'{url}'의 HTML 본문에서 썸네일로 사용할 이미지 찾음.")
            return body_image_url

        logger.warning(f"'{url}'에서 썸네일로 사용할 수 있는 이미지를 찾지 못했습니다.")
        return None

    except requests.RequestException as e:
        logger.error(f"'{url}' 썸네일 추출 중 네트워크 오류 발생: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(
            f"'{url}' 썸네일 추출 중 예기치 않은 오류 발생: {e}", exc_info=True
        )
        return None


def normalize_thumbnail_url(thumbnail_url: str, base_url: str) -> str:
    """
    썸네일 URL을 완전한 절대 경로로 정규화합니다.

    urllib.parse.urljoin을 사용하여 상대 URL을 절대 URL로 안전하게 변환합니다.

    Args:
        thumbnail_url: 정규화할 썸네일 URL.
        base_url: 썸네일 URL이 상대 경로일 경우 기준이 될 URL.

    Returns:
        정규화된 절대 URL. 입력 thumbnail_url이 비어있으면 빈 문자열 반환.
    """
    if not thumbnail_url:
        return ""

    return urljoin(base_url, thumbnail_url)


def extract_text_from_html(html_content: str) -> str:
    """
    HTML 콘텐츠에서 스크립트와 스타일을 제거하고 순수 텍스트를 추출합니다.

    Args:
        html_content: 정제할 HTML 콘텐츠 문자열.

    Returns:
        추출된 텍스트. 내용이 없으면 빈 문자열.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    return soup.get_text(separator="\n", strip=True)


def _extract_image_url_from_html(html: str, base_url: str) -> Optional[str]:
    """
    웹페이지 HTML 본문에서 가장 의미 있는 이미지 URL을 추출합니다.

    Args:
        html: 분석할 HTML 콘텐츠 문자열.
        base_url: 이미지 URL이 상대 경로일 경우 절대 경로로 변환하기 위한 기준 URL.

    Returns:
        추출된 이미지의 절대 URL. 이미지를 찾지 못한 경우 None.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    img_tag = soup.find("img")

    if img_tag and img_tag.get("src"):
        return urljoin(base_url, img_tag["src"])
    return None
