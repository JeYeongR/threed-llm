import feedparser
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from PIL import Image
from io import BytesIO

from src.models.dto import CrawledContentDto
from src.config.blog_config import BLOG_CONFIGS

logger = logging.getLogger(__name__)

class BlogCrawler:
    """블로그 크롤링 클래스"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def crawl_all_sources(self) -> List[CrawledContentDto]:
        """모든 블로그 소스에서 콘텐츠를 크롤링합니다."""
        all_posts = []
        
        for config in BLOG_CONFIGS:
            try:
                logger.info(f"{config['blog_url']} 크롤링 시작")
                posts = self.crawl_blog(config)
                all_posts.extend(posts)
                logger.info(f"{config['blog_url']}에서 {len(posts)}개의 포스트를 크롤링했습니다.")
            except Exception as e:
                logger.error(f"{config['blog_url']} 크롤링 중 오류 발생: {str(e)}")
                continue
                
        return all_posts

    def crawl_blog(self, config: Dict[str, Any]) -> List[CrawledContentDto]:
        """개별 블로그에서 콘텐츠를 크롤링합니다."""
        blog_url = config['blog_url']
        
        if 'naver.com' in blog_url or 'd2.naver.com' in blog_url:
            return self._crawl_naver_blog(blog_url, config.get('max_posts', 5), config.get('name', '네이버 D2'))
        else:
            return self._crawl_generic_blog(blog_url, config)

    def _crawl_naver_blog(self, blog_url: str, max_posts: int, source_name: str = "네이버") -> List[CrawledContentDto]:
        """네이버 D2 블로그를 크롤링합니다. Atom 피드 형식을 파싱합니다.
        
        Args:
            blog_url: 크롤링할 블로그 URL
            max_posts: 최대 크롤링할 포스트 수
            source_name: 블로그 소스 이름 (기본값: "네이버")
        """
        logger.info(f"{source_name} 블로그 크롤링 시작: {blog_url}")
        results = []
        
        try:
            feed = feedparser.parse(blog_url)
            
            for entry in feed.entries[:max_posts]:
                try:
                    title = entry.get('title', '제목 없음')
                    
                    link_obj = entry.get('link', '')
                    if isinstance(link_obj, dict) and 'href' in link_obj:
                        link = link_obj['href']
                    elif isinstance(link_obj, str):
                        link = link_obj
                    else:
                        link = ''
                        if hasattr(entry, 'links'):
                            for link_item in entry.links:
                                if link_item.get('rel') == 'alternate':
                                    link = link_item.get('href', '')
                                    break
                    
                    content = ''
                    if 'content' in entry and len(entry.content) > 0:
                        content = self._extract_text_from_html(entry.content[0].value)
                    elif 'summary' in entry:
                        content = self._extract_text_from_html(entry.summary)
                    
                    published = entry.get('published', entry.get('updated', ''))
                    try:
                        published_at = datetime.strptime(published, '%Y-%m-%dT%H:%M:%S%z')
                    except ValueError:
                        published_at = datetime.now()
                    
                    thumbnail_url = self._extract_thumbnail(entry)
                    
                    if thumbnail_url:
                        logger.info(f"포스트 '{title}' 썸네일 URL: {thumbnail_url}")
                    else:
                        logger.warning(f"포스트 '{title}' 썸네일을 찾을 수 없음")
                    
                    dto = CrawledContentDto(
                        title=title,
                        content=content,
                        url=link,
                        source_name=source_name,
                        thumbnail_url=thumbnail_url,
                        published_at=published_at
                    )
                    
                    results.append(dto)
                    
                except Exception as e:
                    logger.error(f"포스트 처리 중 오류 발생: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Atom 피드 파싱 중 오류 발생: {str(e)}")
            
        return results

    def _crawl_generic_blog(self, blog_url: str, config: Dict[str, Any]) -> List[CrawledContentDto]:
        """일반적인 블로그를 크롤링합니다."""
        # TODO: Playwright를 사용한 일반 블로그 크롤링 구현
        logger.warning(f"일반 블로그 크롤링은 아직 구현되지 않았습니다: {blog_url}")
        return []

    def _extract_thumbnail(self, entry) -> str:
        """엔트리에서 썸네일 URL을 추출합니다."""
        # 1. media_thumbnail 확인
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            logger.info("media_thumbnail에서 썸네일 찾음")
            return entry.media_thumbnail[0]['url']
        
        # 2. 이미지 링크 확인
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.get('type', '').startswith('image'):
                    logger.info("이미지 링크에서 썸네일 찾음")
                    return link.get('href', '')
        
        # 3. 본문에서 이미지 추출
        if hasattr(entry, 'content'):
            for content in entry.content:
                if not hasattr(content, 'value'):
                    continue
                img_match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', content.value, re.IGNORECASE)
                if img_match:
                    logger.info("본문에서 이미지 추출")
                    return img_match.group(1)
        
        # 4. summary에서 이미지 추출
        if hasattr(entry, 'summary'):
            img_match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', entry.summary, re.IGNORECASE)
            if img_match:
                logger.info("요약에서 이미지 추출")
                return img_match.group(1)
                    
        return ""

    def _extract_text_from_html(self, html: str) -> str:
        """HTML에서 텍스트만 추출합니다."""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def process_thumbnail(self, image_url: str) -> Optional[bytes]:
        """썸네일 이미지를 처리합니다."""
        if not image_url:
            return None
            
        try:
            response = self.session.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            img.thumbnail((300, 300))
            
            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"썸네일 처리 중 오류 발생: {str(e)}")
            return None
