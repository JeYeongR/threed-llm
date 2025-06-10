import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

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

    soup = BeautifulSoup(html, "lxml")
    img_tag = soup.find("img")
    if img_tag and img_tag.get("src"):
        return img_tag["src"]
    return ""


def extract_thumbnail_from_webpage(
    session: requests.Session, url: str
) -> Optional[str]:
    """웹페이지에서 썸네일 URL을 추출합니다.

    Args:
        session: requests 세션 객체
        url: 웹페이지 URL

    Returns:
        추출된 썸네일 URL 또는 None
    """
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml")

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"]

        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            return twitter_image["content"]

        image_src_link = soup.find("link", rel="image_src")
        if image_src_link and image_src_link.get("href"):
            return image_src_link["href"]

        logger.warning(f"웹페이지 {url}에서 썸네일 메타 태그를 찾을 수 없습니다.")
        return None

    except requests.RequestException as e:
        logger.error(f"웹페이지 {url}에서 썸네일 추출 중 오류 발생: {e}")
        return None
    except Exception as e:
        logger.error(f"썸네일 추출 중 예기치 않은 오류 발생 ({url}): {e}")
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


def extract_text_from_html(html_content: str) -> str:
    """HTML에서 텍스트를 추출합니다.

    Args:
        html_content: HTML 콘텐츠 문자열

    Returns:
        추출된 텍스트
    """
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "lxml")
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)
