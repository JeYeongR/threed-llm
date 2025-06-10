import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import requests

from src.config.blog_config import BLOG_CONFIGS
from src.models.dto import CrawledContentDto
from src.services.crawler_constants import BLOG_TYPE_TOSS  # 추가
from src.services.crawler_constants import (
    BLOG_TYPE_DEVOCEAN,
    BLOG_TYPE_GENERIC,
    BLOG_TYPE_KAKAO,
    BLOG_TYPE_NAVER,
    DEFAULT_HEADERS,
)
from src.services.crawler_utils import (
    extract_image_url_from_html,
    extract_text_from_html,
    extract_thumbnail_from_webpage,
    normalize_thumbnail_url,
    process_thumbnail_image,
)

logger = logging.getLogger(__name__)


class BlogCrawler:
    """블로그 크롤링 클래스"""

    def __init__(self):
        """크롤러 초기화"""
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def crawl_all_sources(self) -> List[CrawledContentDto]:
        """모든 블로그 소스에서 콘텐츠를 크롤링합니다.

        Returns:
            크롤링된 모든 콘텐츠 목록
        """
        all_posts = []

        for config in BLOG_CONFIGS:
            blog_url = config.get("blog_url", "")
            try:
                logger.info(f"{blog_url} 크롤링 시작")
                posts = self.crawl_blog(config)
                all_posts.extend(posts)
                logger.info(f"{blog_url}에서 {len(posts)}개의 포스트를 크롤링했습니다.")
            except Exception as e:
                logger.error(f"{blog_url} 크롤링 중 오류 발생: {str(e)}")
                continue

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

        if blog_type == BLOG_TYPE_NAVER:
            return self._crawl_naver_blog(
                blog_url, max_posts, source_name or "네이버 D2"
            )
        elif blog_type == BLOG_TYPE_KAKAO:
            return self._crawl_kakao_blog(
                blog_url, max_posts, source_name or "카카오 기술 블로그"
            )
        elif blog_type == BLOG_TYPE_DEVOCEAN:
            return self._crawl_devocean_blog(
                blog_url, max_posts, source_name or "데보션 블로그"
            )
        elif blog_type == BLOG_TYPE_TOSS:
            company_official_name = config.get("company", "")
            return self._crawl_toss_blog(
                blog_url,
                max_posts,
                source_name or "토스 기술 블로그",
                company_official_name,
            )
        else:
            return self._crawl_generic_blog(blog_url, config)

    def _detect_blog_type(self, blog_url: str, config: Dict[str, Any]) -> str:
        """블로그 타입을 감지합니다.

        Args:
            blog_url: 블로그 URL
            config: 블로그 설정 정보

        Returns:
            블로그 타입 식별자
        """
        if "naver.com" in blog_url or "d2.naver.com" in blog_url:
            return BLOG_TYPE_NAVER
        elif "kakao.com" in blog_url or "tech.kakao.com" in blog_url:
            return BLOG_TYPE_KAKAO
        elif "politepol.com" in blog_url and "DEVOCEAN" in config.get("company", ""):
            return BLOG_TYPE_DEVOCEAN
        elif "toss.tech" in blog_url:
            return BLOG_TYPE_TOSS
        else:
            return BLOG_TYPE_GENERIC

    def _crawl_naver_blog(
        self, blog_url: str, max_posts: int, source_name: str = "네이버"
    ) -> List[CrawledContentDto]:
        """네이버 D2 블로그를 크롤링합니다. Atom 피드 형식을 파싱합니다.

        Args:
            blog_url: 크롤링할 블로그 URL
            max_posts: 최대 크롤링할 포스트 수
            source_name: 블로그 소스 이름 (기본값: "네이버")

        Returns:
            크롤링된 블로그 포스트 목록
        """
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []

        try:
            feed = feedparser.parse(blog_url)

            for entry in feed.entries[:max_posts]:
                try:
                    title = (
                        getattr(entry, "title", "제목 없음")
                        if hasattr(entry, "title")
                        else "제목 없음"
                    )

                    link = self._extract_link_from_entry(entry)
                    if not link:
                        logger.warning(f"포스트 '{title}'에서 링크를 찾을 수 없습니다.")
                        continue

                    content = self._extract_content_from_entry(entry)

                    published_date = self._extract_date_from_entry(entry)
                    thumbnail_url = self._extract_thumbnail(entry)
                    thumbnail_data = None
                    if thumbnail_url:
                        thumbnail_data = process_thumbnail_image(
                            self.session, thumbnail_url
                        )

                    post = CrawledContentDto(
                        title=title,
                        content=content,
                        url=link,
                        source_name=source_name,
                        thumbnail_url=thumbnail_url,
                        published_at=published_date,
                    )

                    results.append(post)
                    logger.debug(f"포스트 추가됨: {title}")

                except Exception as e:
                    logger.error(f"포스트 처리 중 오류 발생: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"RSS 피드 파싱 중 오류 발생: {str(e)}")

        return results

    def _extract_link_from_entry(self, entry) -> str:
        """엔트리에서 링크를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 링크 URL
        """
        link_obj = entry.get("link", "")

        if isinstance(link_obj, dict) and "href" in link_obj:
            return link_obj["href"]

        elif isinstance(link_obj, str):
            return link_obj

        elif hasattr(entry, "links"):
            for link_item in entry.links:
                if link_item.get("rel") == "alternate":
                    return link_item.get("href", "")

        return ""

    def _extract_content_from_entry(self, entry) -> str:
        """엔트리에서 콘텐츠를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 콘텐츠 텍스트
        """
        if "content" in entry and len(entry.content) > 0:
            return extract_text_from_html(entry.content[0].value)

        elif "summary" in entry:
            return extract_text_from_html(entry.summary)

        elif "description" in entry:
            return extract_text_from_html(entry.description)

        return ""

    def _extract_date_from_entry(self, entry) -> datetime:
        """엔트리에서 날짜를 추출합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            추출된 날짜 객체
        """
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])

        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])

        return datetime.now()

    def _parse_kakao_date(self, entry) -> datetime:
        """카카오 블로그 날짜 형식을 파싱합니다.

        Args:
            entry: 피드 엔트리 객체

        Returns:
            파싱된 날짜 객체
        """
        published = ""

        if hasattr(entry, "published"):
            published = entry.published
        elif hasattr(entry, "pubDate"):
            published = entry.pubDate
        elif hasattr(entry, "updated"):
            published = entry.updated

        if not published:
            return datetime.now()

        logger.debug(f"발행일 원본 문자열: {published}")

        entry = type("obj", (object,), {"published": published, "updated": published})
        return self._extract_date_from_entry(entry)

    def _crawl_kakao_blog(
        self, blog_url: str, max_posts: int, source_name: str = "카카오"
    ) -> List[CrawledContentDto]:
        """카카오 기술 블로그를 크롤링합니다. RSS 피드 형식을 파싱합니다.

        Args:
            blog_url: 크롤링할 블로그 URL
            max_posts: 최대 크롤링할 포스트 수
            source_name: 블로그 소스 이름 (기본값: "카카오")

        Returns:
            크롤링된 블로그 포스트 목록
        """
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []

        try:
            feed = feedparser.parse(blog_url)

            for entry in feed.entries[:max_posts]:
                try:
                    title = (
                        getattr(entry, "title", "제목 없음")
                        if hasattr(entry, "title")
                        else "제목 없음"
                    )

                    link = self._extract_link_from_entry(entry)
                    if not link:
                        logger.warning(f"포스트 '{title}'에서 링크를 찾을 수 없습니다.")
                        continue

                    content = self._extract_content_from_entry(entry)

                    published_at = self._parse_kakao_date(entry)

                    thumbnail_url = self._extract_thumbnail(entry)
                    thumbnail_data = None
                    if thumbnail_url:
                        logger.debug(f"포스트 '{title}' 썸네일 URL: {thumbnail_url}")
                        thumbnail_data = process_thumbnail_image(
                            self.session, thumbnail_url
                        )

                    dto = CrawledContentDto(
                        title=title,
                        content=content,
                        url=link,
                        source_name=source_name,
                        thumbnail_url=thumbnail_url,
                        company="DEVOCEAN",
                        published_at=published_at,
                    )

                    results.append(dto)
                    logger.debug(f"포스트 추가됨: {title}")

                except Exception as e:
                    logger.error(f"포스트 처리 중 오류 발생: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"RSS 피드 파싱 중 오류 발생: {str(e)}")

        return results

    def _crawl_devocean_blog(
        self, blog_url: str, max_posts: int, source_name: str = "데보션"
    ) -> List[CrawledContentDto]:
        """데보션(DEVOCEAN) 블로그를 크롤링합니다. Politepol로 생성된 RSS 피드를 파싱합니다.

        Args:
            blog_url: 크롤링할 블로그 URL (Politepol 피드 URL)
            max_posts: 최대 크롤링할 포스트 수
            source_name: 블로그 소스 이름 (기본값: "데보션")

        Returns:
            크롤링된 블로그 포스트 목록
        """
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []

        try:
            feed = feedparser.parse(blog_url)

            for entry in feed.entries[:max_posts]:
                try:
                    title = (
                        getattr(entry, "title", "제목 없음")
                        if hasattr(entry, "title")
                        else "제목 없음"
                    )

                    link = self._extract_link_from_entry(entry)
                    if not link:
                        logger.warning(f"포스트 '{title}'에서 링크를 찾을 수 없습니다.")
                        continue

                    content = self._extract_content_from_entry(entry)

                    published_at = self._extract_date_from_entry(entry)

                    thumbnail_url = self._extract_thumbnail(entry)

                    if not thumbnail_url and link:
                        thumbnail_url = extract_thumbnail_from_webpage(
                            self.session, link
                        )

                    thumbnail_data = None
                    if thumbnail_url:
                        logger.debug(f"포스트 '{title}' 썸네일 URL: {thumbnail_url}")
                        thumbnail_data = process_thumbnail_image(
                            self.session, thumbnail_url
                        )
                    else:
                        logger.warning(f"포스트 '{title}' 썸네일을 찾을 수 없음")

                    dto = CrawledContentDto(
                        title=title,
                        content=content,
                        url=link,
                        source_name=source_name,
                        thumbnail_url=thumbnail_url,
                        company="DEVOCEAN",
                        published_at=published_at,
                    )

                    results.append(dto)
                    logger.debug(f"포스트 추가됨: {title}")

                except Exception as e:
                    logger.error(f"포스트 처리 중 오류 발생: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"RSS 피드 파싱 중 오류 발생: {str(e)}")

        return results

    def _crawl_toss_blog(
        self,
        blog_url: str,
        max_posts: int,
        source_name: str = "토스 기술 블로그",
        company_official_name: str = "",
    ) -> List[CrawledContentDto]:
        """토스 기술 블로그를 크롤링합니다. Atom 피드 형식을 파싱합니다.

        Args:
            blog_url: 크롤링할 블로그 URL
            max_posts: 최대 크롤링할 포스트 수
            source_name: 블로그 소스 이름 (기본값: "토스 기술 블로그")

        Returns:
            크롤링된 블로그 포스트 목록
        """
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []
        try:
            feed = feedparser.parse(blog_url)
            for entry in feed.entries[:max_posts]:
                title = entry.get("title", "")
                link = self._extract_link_from_entry(entry)
                content = self._extract_content_from_entry(entry)
                published_date = self._extract_date_from_entry(entry)
                thumbnail_url = self._extract_thumbnail(entry)

                normalized_thumbnail_url = normalize_thumbnail_url(thumbnail_url, link)
                thumbnail_bytes = self.process_thumbnail(normalized_thumbnail_url)

                post_data = CrawledContentDto(
                    title=title,
                    content=content,
                    url=link,
                    source_name=source_name,
                    thumbnail_url=normalized_thumbnail_url,
                    published_at=published_date,
                    company=company_official_name,
                )
                results.append(post_data)
                logger.debug(f"{source_name} 포스트 크롤링 완료: {title}")

        except requests.exceptions.RequestException as e:
            logger.error(f"{source_name} 블로그 요청 중 오류 발생: {e}")
        except Exception as e:
            logger.error(f"{source_name} 블로그 파싱 중 오류 발생: {e}")

        logger.info(f"{source_name} 블로그 크롤링 완료, {len(results)}개 포스트 수집")
        return results

    def _crawl_generic_blog(
        self, blog_url: str, config: Dict[str, Any]
    ) -> List[CrawledContentDto]:
        """일반적인 블로그를 크롤링합니다.

        Args:
            blog_url: 크롤링할 블로그 URL
            config: 블로그 설정 정보 (이름, 회사명, 최대 포스트 수 등)

        Returns:
            크롤링된 블로그 포스트 목록
        """
        # TODO: Playwright를 사용한 일반 블로그 크롤링 구현
        logger.warning(f"일반 블로그 크롤링은 아직 구현되지 않았습니다: {blog_url}")

        source_name = config.get("name", "일반 블로그")
        max_posts = config.get("max_posts", 10)

        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []

        # 여기에 Playwright를 사용한 크롤링 로직 구현 예정
        # 1. Playwright 브라우저 인스턴스 생성
        # 2. 페이지 탐색 및 콘텐츠 추출
        # 3. 제목, 내용, 링크, 날짜, 썸네일 추출
        # 4. CrawledContentDto 생성 및 결과 목록에 추가

        return results

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

    def _extract_text_from_html(self, html: str) -> str:
        """HTML에서 텍스트만 추출합니다.

        Args:
            html: 추출할 HTML 문자열

        Returns:
            추출된 텍스트
        """
        return extract_text_from_html(html)

    def process_thumbnail(self, image_url: str) -> Optional[bytes]:
        """썸네일 이미지를 처리합니다.

        Args:
            image_url: 처리할 이미지 URL

        Returns:
            처리된 이미지 바이트 데이터 또는 오류 발생 시 None
        """
        if not image_url:
            return None

        logger.debug(f"썸네일 처리 시작: {image_url}")
        return process_thumbnail_image(self.session, image_url)
