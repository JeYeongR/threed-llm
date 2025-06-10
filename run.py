import argparse
import logging
import sys
from typing import Any, Callable

from dotenv import load_dotenv

from src.config.api_config import OPENAI_API_KEY
from src.config.blog_config import BLOG_CONFIGS
from src.models.dto import CrawledContentDto
from src.models.enums import Company
from src.services.crawler import BlogCrawler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Setup and return the argument parser."""
    parser = argparse.ArgumentParser(description="기술 블로그 크롤링 및 요약 도구")

    parser.add_argument(
        "mode",
        nargs='?',
        default="crawl",
        choices=["crawl", "crawl-only", "delete-only"],
        help="실행 모드를 선택합니다 (기본값: 'crawl'). 'crawl'(크롤링, 처리, 저장), 'crawl-only'(크롤링만), 'delete-only'(삭제만)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=5,
        help="각 블로그에서 크롤링할 최대 포스트 수 (기본값: 5)",
    )
    company_choices = [company.name for company in Company] + ["ALL"]
    parser.add_argument(
        "--company",
        type=str.upper,
        choices=company_choices,
        default="ALL",
        help="크롤링할 회사 선택 (기본값: ALL)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="[crawl 모드 전용] 지정된 회사의 모든 포스트를 크롤링 전에 데이터베이스에서 삭제합니다. 'ALL' 회사에는 적용되지 않습니다.",
    )
    return parser


def _get_target_configs(company_arg: str) -> list:
    """Helper function to get target blog configurations based on company argument."""
    if company_arg == "ALL":
        return BLOG_CONFIGS

    target_configs = [config for config in BLOG_CONFIGS if config["company"].name == company_arg]
    if not target_configs:
        logger.warning(f"{company_arg}에 해당하는 블로그 설정이 없습니다.")
    return target_configs


def _run_crawler(target_configs: list, max_posts: int) -> list[CrawledContentDto]:
    """Helper function to run the crawler and return crawled posts."""
    crawler = BlogCrawler()
    logger.info(f"크롤링을 시작합니다... (대상: {len(target_configs)}개 블로그)")
    crawled_posts = crawler.crawl_all_sources(configs=target_configs, max_posts=max_posts)
    logger.info(f"총 {len(crawled_posts)}개의 포스트를 크롤링했습니다.")
    return crawled_posts


def run_crawl_and_process(
    args: argparse.Namespace,
    delete_posts_by_company: Callable[[str], None],
    process_posts: Callable[[list[CrawledContentDto]], list[Any]],
    save_to_rds: Callable[[list[Any]], tuple[int, int]],
) -> int:
    """Crawl, process, and save posts."""
    if args.clear:
        if args.company == "ALL":
            logger.error("'ALL' 회사에 대해 --clear 옵션을 사용할 수 없습니다. 특정 회사를 지정해주세요.")
            return 1
        company_to_clear = args.company
        logger.info(f"{company_to_clear} 회사의 모든 포스트를 데이터베이스에서 삭제합니다...")
        delete_posts_by_company(company_to_clear)
        logger.info(f"{company_to_clear} 회사의 포스트 삭제 완료.")

    target_configs = _get_target_configs(args.company)
    if not target_configs:
        return 0

    try:
        crawled_posts = _run_crawler(target_configs, args.max_posts)

        if not crawled_posts:
            logger.info("저장할 포스트가 없습니다.")
            return 0

        logger.info("포스트 처리 중...")
        processed_posts = process_posts(crawled_posts)

        logger.info("RDS에 저장 중...")
        saved, errors = save_to_rds(processed_posts)
        logger.info(f"RDS 저장 완료: {saved}개 성공, {errors}개 실패")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}", exc_info=True)
        return 1
    return 0


def run_crawl_only(args: argparse.Namespace) -> int:
    """Crawl and print posts without saving."""
    target_configs = _get_target_configs(args.company)
    if not target_configs:
        return 0

    try:
        crawled_posts = _run_crawler(target_configs, args.max_posts)

        for i, post in enumerate(crawled_posts, 1):
            logger.info(f"[{i}] {post.title}")
            logger.info(f"    URL: {post.url}")
            logger.info(f"    출처: {post.source_name}")
            logger.info(f"    발행일: {post.published_at}")
            logger.info("=" * 50)

    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {e}", exc_info=True)
        return 1
    return 0


def run_delete_only(args: argparse.Namespace, delete_posts_by_company: Callable[[str], None]) -> int:
    """Delete posts without crawling."""
    if args.company == "ALL":
        logger.error("'ALL' 회사에 대해 삭제 옵션을 사용할 수 없습니다. 특정 회사를 지정해주세요.")
        return 1

    try:
        company_to_clear = args.company
        logger.info(f"{company_to_clear} 회사의 모든 포스트를 데이터베이스에서 삭제합니다...")
        delete_posts_by_company(company_to_clear)
        logger.info(f"{company_to_clear} 회사의 포스트 삭제 완료.")

    except Exception as e:
        logger.error(f"삭제 중 오류 발생: {e}", exc_info=True)
        return 1
    return 0


def main() -> int:
    """Main entry point of the application."""
    parser = setup_parser()
    args = parser.parse_args()

    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        logger.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return 1

    from src.database import init_db

    init_db()
    from src.core.db_handler import delete_posts_by_company, save_to_rds
    from src.core.post_processor import process_posts

    try:
        if args.mode == "crawl":
            return run_crawl_and_process(args, delete_posts_by_company, process_posts, save_to_rds)
        elif args.mode == "crawl-only":
            return run_crawl_only(args)
        elif args.mode == "delete-only":
            return run_delete_only(args, delete_posts_by_company)
        else:
            parser.print_help()
            return 1

    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
