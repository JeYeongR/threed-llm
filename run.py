import argparse
import logging
import sys

from dotenv import load_dotenv

from src.services.crawler_constants import BlogType

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def setup_parser():
    """Setup and return the argument parser."""
    parser = argparse.ArgumentParser(description="기술 블로그 크롤링 및 요약 도구")

    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="크롤링만 수행하고 요약 및 저장은 건너뜁니다",
    )

    parser.add_argument(
        "--summarize-only",
        action="store_true",
        help="이미 크롤링된 콘텐츠를 요약만 합니다",
    )

    parser.add_argument(
        "--max-posts",
        type=int,
        default=5,
        help="각 블로그에서 크롤링할 최대 포스트 수 (기본값: 5)",
    )

    company_choices = [blog_type.name for blog_type in BlogType] + ["ALL"]
    parser.add_argument(
        "--company",
        type=str.upper,
        choices=company_choices,
        default="ALL",
        help="크롤링할 회사 선택 (기본값: ALL)",
    )

    return parser


def run_crawl_and_process(args: argparse.Namespace):
    """Crawl, process, and save posts."""
    from src.config.blog_config import BLOG_CONFIGS
    from src.core.db_handler import save_to_rds
    from src.core.post_processor import process_posts
    from src.services.crawler import BlogCrawler

    try:
        if args.company == "ALL":
            target_configs = BLOG_CONFIGS
        else:
            target_configs = [
                config
                for config in BLOG_CONFIGS
                if config.get("company") == args.company
            ]

        if not target_configs:
            logger.warning(f"{args.company}에 해당하는 블로그 설정이 없습니다.")
            return 0

        crawler = BlogCrawler()
        logger.info(f"크롤링을 시작합니다... (대상: {args.company})")

        crawled_posts = crawler.crawl_all_sources(
            configs=target_configs, max_posts=args.max_posts
        )
        logger.info(f"총 {len(crawled_posts)}개의 포스트를 크롤링했습니다.")

        if not crawled_posts:
            logger.info("저장할 포스트가 없습니다.")
            return 0

        logger.info("포스트 처리 중...")
        processed_posts = process_posts(crawled_posts)

        logger.info("RDS에 저장 중...")
        saved, errors = save_to_rds(processed_posts)
        logger.info(f"RDS 저장 완료: {saved}개 성공, {errors}개 실패")

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {str(e)}")
        return 1
    return 0


def run_crawl_only(args: argparse.Namespace):
    """Crawl and print posts without saving."""
    from src.config.blog_config import BLOG_CONFIGS
    from src.services.crawler import BlogCrawler

    try:
        if args.company == "ALL":
            target_configs = BLOG_CONFIGS
        else:
            target_configs = [
                config
                for config in BLOG_CONFIGS
                if config.get("company") == args.company
            ]

        if not target_configs:
            logger.warning(f"{args.company}에 해당하는 블로그 설정이 없습니다.")
            return 0

        crawler = BlogCrawler()
        logger.info(f"크롤링을 시작합니다... (대상: {args.company})")

        crawled_posts = crawler.crawl_all_sources(
            configs=target_configs, max_posts=args.max_posts
        )
        logger.info(f"총 {len(crawled_posts)}개의 포스트를 크롤링했습니다.")

        for i, post in enumerate(crawled_posts, 1):
            logger.info(f"[{i}] {post.title}")
            logger.info(f"    URL: {post.url}")
            logger.info(f"    출처: {post.source_name}")
            logger.info(f"    발행일: {post.published_at}")
            logger.info("=" * 50)

    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")
        return 1
    return 0


def run_summarize_only():
    """Summarize already crawled content (not implemented)."""
    logger.error("요약만 실행하는 기능은 아직 구현되지 않았습니다.")
    return 1


def main():
    """Main entry point of the application."""
    parser = setup_parser()
    args = parser.parse_args()

    try:
        from src.config.api_config import OPENAI_API_KEY

        if not OPENAI_API_KEY:
            logger.error(
                "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요."
            )
            return 1

        if args.crawl_only:
            return run_crawl_only(args)
        elif args.summarize_only:
            return run_summarize_only()
        else:
            return run_crawl_and_process(args)

    except Exception as e:
        logger.error(f"실행 중 오류 발생: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
