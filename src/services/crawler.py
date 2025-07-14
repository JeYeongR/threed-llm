import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import feedparser
import requests

from src.config.blog_config import BLOG_CONFIGS
from src.models.dto import CrawledContentDto
from src.models.enums import Company
from src.services.crawler_constants import DEFAULT_HEADERS, BlogType
from src.services.crawler_utils import (
    extract_text_from_html,
    extract_thumbnail_from_webpage,
    normalize_thumbnail_url,
)

logger = logging.getLogger(__name__)


class BlogCrawler:
    """블로그 크롤링을 담당하는 클래스"""

    def __init__(self):
        """크롤러 초기화"""
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def crawl_all_sources(
        self, configs: List[Dict[str, Any]], max_posts: int
    ) -> List[CrawledContentDto]:
        """지정된 설정에 따라 모든 블로그 소스를 크롤링합니다."""
        all_posts = []
        for config in configs:
            try:
                posts = self._crawl_blog(config, max_posts)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(
                    f"{config.get('name', '알 수 없는')} 블로그 크롤링 중 오류: {e}"
                )
        return all_posts

    def _crawl_blog(
        self, config: Dict[str, Any], max_posts: int
    ) -> List[CrawledContentDto]:
        """개별 블로그를 크롤링하고 처리합니다."""
        blog_url = config.get("blog_url")
        if not blog_url:
            logger.error("URL이 설정되지 않은 블로그 설정이 있습니다.")
            return []

        blog_type = self._detect_blog_type(blog_url, config)
        if blog_type is None:
            logger.warning(
                f"알 수 없는 블로그 타입입니다: {blog_url}. 이 블로그는 건너뜁니다."
            )
            return []
        feed = feedparser.parse(blog_url)

        source_name_cfg = config.get("name")
        company_cfg = config.get("company")

        parser = self._parse_default_feed
        entries = parser(feed, max_posts)

        return self._process_feed(blog_url, source_name_cfg, company_cfg, entries)

    def _parse_default_feed(self, feed, max_posts: int) -> List[Dict[str, Any]]:
        """기본 RSS/Atom 피드를 파싱합니다."""
        logger.debug(
            f"Parsing feed using _parse_default_feed for up to {max_posts} posts."
        )
        return feed.entries[:max_posts]

    def _process_feed(
        self,
        blog_url: str,
        source_name_from_config: Optional[str],
        company_obj: Company,
        entries: List[Dict[str, Any]],
    ) -> List[CrawledContentDto]:
        """피드 항목을 CrawledContentDto 객체로 변환합니다."""
        final_source_name = (
            source_name_from_config
            if source_name_from_config is not None
            else f"Unknown Blog ({blog_url})"
        )

        logger.info(f"{final_source_name} 블로그 크롤링 시작: {blog_url}")
        results = []
        try:
            for entry in entries:
                title = entry.get("title", "제목 없음")
                link = self._extract_link_from_entry(entry)
                if not link:
                    logger.warning(
                        f"포스트 '{title}' ({final_source_name})에서 링크를 찾을 수 없어 건너뜁니다."
                    )
                    continue

                content_text = self._extract_content_from_entry(entry)
                published_date = self._extract_date_from_entry(entry)
                thumbnail_url = self._extract_thumbnail(entry)

                if not thumbnail_url and link:
                    try:
                        logger.debug(
                            f"피드에서 썸네일을 찾지 못했습니다. 웹페이지에서 추출 시도: {link} ({final_source_name})"
                        )
                        thumbnail_url = extract_thumbnail_from_webpage(
                            self.session, link
                        )
                        if thumbnail_url:
                            logger.debug(
                                f"웹페이지에서 썸네일 추출 성공: {thumbnail_url} ({final_source_name})"
                            )
                        else:
                            logger.debug(
                                f"웹페이지 {link}에서 썸네일을 찾지 못했습니다. ({final_source_name})"
                            )
                    except Exception as e_webpage_thumb:
                        logger.warning(
                            f"웹페이지 {link}에서 썸네일 추출 중 오류 발생 ({final_source_name}): {e_webpage_thumb}"
                        )
                        thumbnail_url = None

                normalized_thumbnail_url = normalize_thumbnail_url(thumbnail_url, link)

                company_enum_member: Company = company_obj

                post_data = CrawledContentDto(
                    title=title,
                    content=content_text,
                    url=link,
                    source_name=final_source_name,
                    thumbnail_url=normalized_thumbnail_url,
                    published_at=published_date,
                    company=company_enum_member,
                )
                results.append(post_data)
                logger.debug(f"{final_source_name} 포스트 크롤링 완료: {title}")

        except requests.exceptions.RequestException as e:
            logger.error(
                f"{final_source_name} 블로그 ({blog_url}) 요청 중 오류 발생: {e}"
            )
        except Exception as e:
            logger.error(
                f"{final_source_name} 블로그 ({blog_url}) 파싱 중 오류 발생: {e}"
            )

        logger.info(
            f"{final_source_name} 블로그 크롤링 완료, {len(results)}개 포스트 수집"
        )
        return results

    def _detect_blog_type(
        self, blog_url: str, config: Dict[str, Any]
    ) -> Union[BlogType, None]:
        """블로그 타입을 감지합니다. (match-case 사용)

        Args:
            blog_url: 블로그 URL
            config: 블로그 설정 정보

        Returns:
            블로그 타입 식별자 또는 None
        """
        try:
            parsed_url = urlparse(blog_url)
            hostname = parsed_url.hostname if parsed_url.hostname else ""
            path = parsed_url.path
        except ValueError:
            logger.warning(f"잘못된 형식의 URL입니다: {blog_url}")
            return None

        match hostname:
            case "d2.naver.com":
                return BlogType.NAVER
            case "tech.kakao.com":
                return BlogType.KAKAO
            case "politepol.com":
                if config.get("company") == Company.DEVOCEAN:
                    return BlogType.DEVOCEAN
            case "toss.tech":
                return BlogType.TOSS
            case "daangn.com":
                return BlogType.DAANGN
            case "oliveyoung.tech":
                return BlogType.OLIVE_YOUNG
            case "techblog.lycorp.co.jp":
                return BlogType.LINE
            case "medium.com":
                if path == "/feed/daangn":
                    return BlogType.DAANGN
                elif path == "/feed/myrealtrip-product":
                    return BlogType.MY_REAL_TRIP
            case _:
                pass

        logger.warning(f"알 수 없는 블로그 URL 패턴입니다 (match-case): {blog_url}")
        return None

    def _extract_thumbnail(self, entry) -> str:
        """엔트리에서 썸네일 URL을 추출합니다."""
        if hasattr(entry, "thumbnail"):
            logger.info("thumbnail 태그에서 썸네일 찾음")
            return entry.thumbnail

        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            logger.info("media_thumbnail에서 썸네일 찾음")
            return entry.media_thumbnail[0]["url"]

        if hasattr(entry, "links"):
            for link in entry.links:
                if link.get("type", "").startswith("image"):
                    logger.info("이미지 링크에서 썸네일 찾음")
                    return link.get("href", "")

        if hasattr(entry, "content"):
            for content in entry.content:
                if not hasattr(content, "value"):
                    continue
                img_match = re.search(
                    r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', content.value, re.IGNORECASE
                )
                if img_match:
                    logger.info("본문에서 이미지 추출")
                    return img_match.group(1)

        if hasattr(entry, "summary"):
            img_match = re.search(
                r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', entry.summary, re.IGNORECASE
            )
            if img_match:
                logger.info("요약에서 이미지 추출")
                return img_match.group(1)

        return ""

    def _extract_link_from_entry(self, entry) -> str:
        """피드 엔트리에서 링크를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 링크 URL 문자열
        """
        if hasattr(entry, "link"):
            return entry.link
        return ""

    def _extract_content_from_entry(self, entry) -> str:
        """피드 엔트리에서 콘텐츠를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 콘텐츠 문자열
        """
        content = ""
        if "content" in entry and len(entry.content) > 0:
            content = extract_text_from_html(entry.content[0].value)
        elif "summary" in entry:
            content = extract_text_from_html(entry.summary)
        return content

    def _extract_date_from_entry(self, entry) -> datetime:
        """피드 엔트리에서 날짜를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 날짜 datetime 객체
        """
        published = ""

        if hasattr(entry, "published"):
            published = entry.published
        elif hasattr(entry, "updated"):
            published = entry.updated

        date_formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for date_format in date_formats:
            try:
                return datetime.strptime(published, date_format)
            except (ValueError, TypeError):
                continue

        logger.warning(f"날짜 파싱 실패: {published}, 현재 시간으로 대체")
        return datetime.now()
