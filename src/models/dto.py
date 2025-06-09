from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawledContentDto:
    """크롤링된 콘텐츠 데이터 전송 객체"""

    title: str
    content: str
    url: str
    source_name: str
    thumbnail_url: str
    published_at: datetime


@dataclass
class LlmResponseDto:
    """LLM 응답 데이터 전송 객체"""

    summary: str
    field: str


@dataclass
class CompanyPost:
    """회사 블로그 포스트 데이터 전송 객체"""

    title: str
    summary: str
    thumbnail_url: str
    field: str  # Field enum으로 변환됨
    published_at: datetime
    company: str  # Company enum으로 변환됨
    url: str
    id: Optional[int] = None
