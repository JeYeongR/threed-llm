import logging
import re
from datetime import datetime
from typing import Any, Dict, List

import feedparser
import requests

from src.models.dto import CrawledContentDto
from src.services.crawler_constants import DEFAULT_HEADERS, BlogType
from src.services.crawler_utils import (
    extract_text_from_html,
    extract_thumbnail_from_webpage,
    normalize_thumbnail_url,
)

logger = logging.getLogger(__name__)


class BlogCrawler:
    """블로그 크롤링 클래스"""

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
                # Pass max_posts to crawl_blog if it's not set in the individual config
                if "max_posts" not in config:
                    config["max_posts"] = max_posts
                posts = self.crawl_blog(config)
                all_posts.extend(posts)
            except Exception as e:
                logger.error(
                    f"{config.get('name', '알 수 없는')} 블로그 크롤링 중 오류: {e}"
                )
        return all_posts

    def crawl_blog(self, config: Dict[str, Any]) -> List[CrawledContentDto]:
        """개별 블로그에서 콘텐츠를 크롤링합니다.

        Args:
            config: 블로그 설정 정보

        Returns:
            크롤링된 블로그 콘텐츠 목록
        """
        blog_url = config.get("blog_url", "")
        if not blog_url:
            logger.error("블로그 URL이 제공되지 않았습니다.")
            return []

        blog_type = self._detect_blog_type(blog_url, config)
        max_posts = config.get("max_posts", 5)
        source_name = config.get("name", "")

        source_name_cfg = config.get("name", "")
        company_name_cfg = config.get("company", "")

        effective_source_name = source_name_cfg
        effective_company_name = company_name_cfg

        if blog_type == BlogType.NAVER:
            effective_source_name = source_name_cfg or "네이버 D2"
            effective_company_name = company_name_cfg or "NAVER"
        elif blog_type == BlogType.KAKAO:
            effective_source_name = source_name_cfg or "카카오 기술 블로그"
            effective_company_name = company_name_cfg or "KAKAO"
        elif blog_type == BlogType.DEVOCEAN:
            effective_source_name = source_name_cfg or "데보션 블로그"
            effective_company_name = company_name_cfg or "DEVOCEAN"
        elif blog_type == BlogType.TOSS:
            effective_source_name = source_name_cfg or "토스 기술 블로그"
            effective_company_name = company_name_cfg or "TOSS"
        else:  # BlogType.GENERIC or any other
            effective_source_name = source_name_cfg or f"Unknown Blog ({blog_url})"
            effective_company_name = company_name_cfg or "Unknown Company"

        return self._process_feed(
            blog_url, max_posts, effective_source_name, effective_company_name
        )

    def _process_feed(
        self,
        blog_url: str,
        max_posts: int,
        source_name: str,
        company_name: str,
    ) -> List[CrawledContentDto]:
        """공통 피드 처리 로직. RSS/Atom 피드를 파싱하여 DTO 리스트를 반환합니다."""
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []
        try:
            feed = feedparser.parse(blog_url)
            for entry in feed.entries[:max_posts]:
                title = entry.get("title", "제목 없음")
                link = self._extract_link_from_entry(entry)
                if not link:
                    logger.warning(
                        f"포스트 '{title}' ({source_name})에서 링크를 찾을 수 없어 건너뜁니다."
                    )
                    continue

                content_text = self._extract_content_from_entry(entry)
                published_date = self._extract_date_from_entry(entry)
                thumbnail_url = self._extract_thumbnail(entry)

                if not thumbnail_url and link:
                    try:
                        logger.debug(
                            f"피드에서 썸네일을 찾지 못했습니다. 웹페이지에서 추출 시도: {link} ({source_name})"
                        )
                        thumbnail_url = extract_thumbnail_from_webpage(
                            self.session, link
                        )
                        if thumbnail_url:
                            logger.debug(
                                f"웹페이지에서 썸네일 추출 성공: {thumbnail_url} ({source_name})"
                            )
                        else:
                            logger.debug(
                                f"웹페이지 {link}에서 썸네일을 찾지 못했습니다. ({source_name})"
                            )
                    except Exception as e_webpage_thumb:
                        logger.warning(
                            f"웹페이지 {link}에서 썸네일 추출 중 오류 발생 ({source_name}): {e_webpage_thumb}"
                        )
                        thumbnail_url = None

                normalized_thumbnail_url = normalize_thumbnail_url(thumbnail_url, link)

                post_data = CrawledContentDto(
                    title=title,
                    content=content_text,
                    url=link,
                    source_name=source_name,
                    thumbnail_url=normalized_thumbnail_url,
                    published_at=published_date,
                    company=company_name,
                )
                results.append(post_data)
                logger.debug(f"{source_name} 포스트 크롤링 완료: {title}")

        except requests.exceptions.RequestException as e:
            logger.error(f"{source_name} 블로그 ({blog_url}) 요청 중 오류 발생: {e}")
        except Exception as e:
            logger.error(f"{source_name} 블로그 ({blog_url}) 파싱 중 오류 발생: {e}")

        logger.info(f"{source_name} 블로그 크롤링 완료, {len(results)}개 포스트 수집")
        return results

    def _detect_blog_type(self, blog_url: str, config: Dict[str, Any]) -> BlogType:
        """블로그 타입을 감지합니다.

        Args:
            blog_url: 블로그 URL
            config: 블로그 설정 정보

        Returns:
            블로그 타입 식별자
        """
        if "naver.com" in blog_url or "d2.naver.com" in blog_url:
            return BlogType.NAVER
        elif "kakao.com" in blog_url or "tech.kakao.com" in blog_url:
            return BlogType.KAKAO
        elif "politepol.com" in blog_url and "DEVOCEAN" in config.get("company", ""):
            return BlogType.DEVOCEAN
        elif "toss.tech" in blog_url:
            return BlogType.TOSS
        else:
            return BlogType.GENERIC

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
