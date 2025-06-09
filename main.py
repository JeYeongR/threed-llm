import os
import sys
import logging
import requests
from datetime import datetime
from typing import List, Tuple
from io import BytesIO

from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

from crawler import BlogCrawler
from database import init_db, get_db, DBCompanyPost
from models import CompanyPost, Company, Field, CrawledContentDto
from summarizer import summarize_content
from config import BLOG_CONFIGS
from s3_uploader import s3_uploader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from database import init_db, DBCompanyPost, get_db
from config import BLOG_CONFIGS

# 환경 변수 로드
load_dotenv()

def save_to_rds(posts: List[CompanyPost]) -> tuple[int, int]:
    """RDS에 포스트 저장"""
    saved_count = 0
    error_count = 0
    
    init_db()
    
    db_gen = get_db()
    db = next(db_gen, None)
    
    if db is None:
        logger.error("데이터베이스 세션을 가져올 수 없습니다.")
        return 0, len(posts)
    
    try:
        for post in posts:
            try:
                try:
                    url_to_check = post.url
                    if isinstance(url_to_check, dict) and 'href' in url_to_check:
                        url_to_check = url_to_check['href']
                    
                    logger.debug(f"URL 체크: {url_to_check}")
                    exists = db.query(DBCompanyPost).filter(DBCompanyPost.source_url == url_to_check).first()
                    if exists:
                        logger.info(f"이미 존재하는 포스트: {post.title}")
                        error_count += 1
                        continue
                except Exception as e:
                    logger.error(f"URL 체크 오류: {str(e)}")
                    error_count += 1
                    continue

                url_to_save = post.url
                if isinstance(url_to_save, dict) and 'href' in url_to_save:
                    url_to_save = url_to_save['href']
                
                summary_content = None
                if hasattr(post, 'summary') and post.summary:
                    summary_content = post.summary
                
                db_post = DBCompanyPost(
                    title=post.title,
                    content=summary_content,
                    field=post.field,
                    company=post.company,
                    source_url=url_to_save,
                    thumbnail_image_url=post.thumbnail_url,
                    published_at=post.published_at,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    view_count=0
                )

                db.add(db_post)
                db.commit()
                saved_count += 1
                logger.info(f"RDS 저장 성공: {post.title}")
                
            except IntegrityError as e:
                db.rollback()
                logger.error(f"무결성 오류 ({post.title}): {str(e)}")
                error_count += 1
                
    except Exception as e:
        db.rollback()
        logger.error(f"데이터베이스 오류: {str(e)}")
        error_count = len(posts) - saved_count  
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
    
    return saved_count, error_count

def process_posts(crawled_posts: List[CrawledContentDto]) -> List[CompanyPost]:
    """크롤링된 포스트를 처리하고 요약을 추가합니다."""
    processed_posts = []
    crawler = BlogCrawler()
    
    init_db()
    db_gen = get_db()
    db = next(db_gen, None)
    
    if db is None:
        logger.error("데이터베이스 세션을 가져올 수 없습니다. 중복 검사 없이 처리합니다.")
    
    for i, crawled in enumerate(crawled_posts, 1):
        try:
            logger.info(f"[{i}/{len(crawled_posts)}] '{crawled.title}' 처리 중...")
            
            url_to_check = crawled.url
            if isinstance(url_to_check, dict) and 'href' in url_to_check:
                url_to_check = url_to_check['href']
                
            if db is not None:
                exists = db.query(DBCompanyPost).filter(DBCompanyPost.source_url == url_to_check).first()
                if exists:
                    logger.info(f"  - 이미 저장된 포스트: {crawled.title} (요약 및 저장 건너뜀)")
                    continue
            
            logger.info("  - 요약 생성 중...")
            summary_result = summarize_content(crawled.content)
            
            logger.info("  - 썸네일 처리 중...")
            thumbnail_url = crawled.thumbnail_url
            
            company_name = None
            for config in BLOG_CONFIGS:  
                if config['name'] == crawled.source_name:
                    company_name = config['company']
                    break
            
            if thumbnail_url:
                try:
                    logger.info(f"    - 썸네일 다운로드 중: {thumbnail_url}")
                    response = requests.get(thumbnail_url, timeout=10)
                    response.raise_for_status()
                    
                    # S3에 업로드
                    logger.info("    - S3에 썸네일 업로드 중...")
                    s3_url = s3_uploader.upload_image(
                        response.content,
                        company_name=company_name.lower() if company_name else None,
                        original_filename=thumbnail_url.split('/')[-1] if '/' in thumbnail_url else None
                    )
                    
                    if s3_url:
                        logger.info(f"    - S3 업로드 성공: {s3_url}")
                        thumbnail_url = s3_url
                    else:
                        logger.warning("    - S3 업로드 실패, 원본 URL 사용")
                except Exception as e:
                    logger.error(f"    - 썸네일 처리 중 오류 발생: {str(e)}")
            
            try:
                company = Company[company_name] if company_name else Company.ETC
            except KeyError:
                company = Company.ETC
            
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
            logger.info(f"  ✓ 처리 완료: {crawled.title}")
            
        except Exception as e:
            logger.error(f"  ! 처리 실패 ({crawled.title}): {str(e)}")
    
    return processed_posts

def main():
    """메인 함수"""
    logger.info("블로그 크롤링을 시작합니다...")
    
    try:
        crawler = BlogCrawler()
        logger.info("크롤링을 시작합니다...")
        
        crawled_posts = crawler.crawl_all_sources()
        logger.info(f"총 {len(crawled_posts)}개의 포스트를 크롤링했습니다.")
        
        if not crawled_posts:
            logger.info("저장할 포스트가 없습니다.")
            return
            
        logger.info("포스트 처리 중...")
        processed_posts = process_posts(crawled_posts)
        
        logger.info("RDS에 저장 중...")
        saved, errors = save_to_rds(processed_posts)
        logger.info(f"RDS 저장 완료: {saved}개 성공, {errors}개 실패")
                
    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        sys.exit(1)
