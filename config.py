from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
    raise ValueError("OPENAI_API_KEY가 .env 파일에 제대로 설정되지 않았습니다.")

BLOG_CONFIGS = [
    {
        "blog_url": "https://d2.naver.com/d2.atom",
        "name": "네이버 기술 블로그",
        "company": "NAVER",
        "max_posts": 1
    },
    {
        "blog_url": "https://tech.kakao.com/",
        "name": "카카오 기술 블로그",
        "company": "KAKAO",
        "max_posts": 5
    },
    {
        "blog_url": "https://engineering.linecorp.com/ko/blog/",
        "name": "라인 엔지니어링 블로그",
        "company": "LINE",
        "max_posts": 5
    },
    {
        "blog_url": "https://toss.tech/",
        "name": "토스 기술 블로그",
        "company": "TOSS",
        "max_posts": 5
    }
]
