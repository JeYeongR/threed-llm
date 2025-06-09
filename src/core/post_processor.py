import logging
from typing import List, Tuple
import requests
from datetime import datetime

from src.models.dto import CrawledContentDto, CompanyPost
from src.models.enums import Field, Company
from src.database import init_db, get_db, DBCompanyPost
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
                logger.info(f"  - 이미 저장된 포스트: {crawled.title} (요약 및 저장 건너뜀)")
                continue
            
            logger.info(f"  - 콘텐츠 요약 중...")
            summary_result = summarize_content(crawled.content)
            
            company_name = _get_company_name(crawled.source_name)
            company = _get_company_enum(company_name)
            
            logger.info(f"  - 썸네일 처리 중...")
            thumbnail_url = _process_thumbnail(crawled.thumbnail_url, company_name)
            
            processed_post = CompanyPost(
                title=crawled.title,
                summary=summary_result["summary"],
                thumbnail_url=thumbnail_url,
                field=Field(summary_result["field"]),
                published_at=crawled.published_at,
                company=company,
                url=crawled.url
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
        logger.error("데이터베이스 세션을 가져올 수 없습니다. 중복 검사 없이 처리합니다.")
    
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
        
    url_to_check = crawled.url
    if isinstance(url_to_check, dict) and 'href' in url_to_check:
        url_to_check = url_to_check['href']
        
    return db_session[0].query(DBCompanyPost).filter(DBCompanyPost.source_url == url_to_check).first() is not None

def _get_company_name(source_name):
    """소스 이름에서 회사 이름을 찾습니다."""
    from src.config.blog_config import BLOG_CONFIGS
    
    for config in BLOG_CONFIGS:  
        if config['name'] == source_name:
            return config['company']
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
            original_filename=thumbnail_url.split('/')[-1] if '/' in thumbnail_url else None
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
