from typing import List, TypedDict

from src.models.enums import Company


class BlogConfig(TypedDict):
    """
    개별 블로그 설정을 위한 타입 정의입니다.

    Attributes:
        blog_url: 블로그의 RSS/Atom 피드 URL.
        name: 블로그의 이름 (표시용).
        company: Company Enum으로 정의된 회사 식별자.
    """

    blog_url: str
    name: str
    company: Company


BLOG_CONFIGS: List[BlogConfig] = [
    {
        "blog_url": "https://d2.naver.com/d2.atom",
        "name": "네이버 기술 블로그",
        "company": Company.NAVER,
    },
    {
        "blog_url": "https://tech.kakao.com/feed",
        "name": "카카오 기술 블로그",
        "company": Company.KAKAO,
    },
    {
        "blog_url": "https://politepol.com/fd/XiV8r39FL4YI",
        "name": "데보션 기술 블로그",
        "company": Company.DEVOCEAN,
    },
    {
        "blog_url": "https://toss.tech/atom.xml",
        "name": "토스 기술 블로그",
        "company": Company.TOSS,
    },
    {
        "blog_url": "https://medium.com/feed/myrealtrip-product",
        "name": "마이리얼트립 기술 블로그",
        "company": Company.MY_REAL_TRIP,
    },
    {
        "blog_url": "https://techblog.lycorp.co.jp/ko/feed/index.xml",
        "name": "라인 기술 블로그",
        "company": Company.LINE,
    },
    {
        "blog_url": "https://medium.com/feed/daangn",
        "name": "당근마켓 기술 블로그",
        "company": Company.DAANGN,
    },
    {
        "blog_url": "https://oliveyoung.tech/rss.xml",
        "name": "올리브영 기술 블로그",
        "company": Company.OLIVE_YOUNG,
    },
]
