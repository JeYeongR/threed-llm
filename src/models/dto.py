from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.models.enums import Company, Field


@dataclass
class CrawledContentDto:
    """
    웹에서 직접 크롤링된 초기 콘텐츠 데이터를 나타냅니다.

    Attributes:
        title: 게시물의 제목.
        content: 게시물의 원본 내용 (HTML 또는 텍스트).
        url: 게시물의 원본 URL.
        source_name: 콘텐츠 출처의 이름 (예: 블로그 이름).
        thumbnail_url: 게시물의 썸네일 이미지 URL.
        published_at: 게시물의 발행 일시.
        company: 게시물을 발행한 회사 (Company Enum).
    """

    title: str
    content: str
    url: str
    source_name: str
    thumbnail_url: str
    published_at: datetime
    company: Company


@dataclass
class LlmResponseDto:
    """
    LLM으로부터 받은 요약 및 분야 분석 결과를 나타냅니다.

    Attributes:
        summary: LLM이 생성한 게시물 요약.
        field: LLM이 분석한 게시물의 기술 분야 (Field Enum, Optional).
    """

    summary: str
    field: Optional[Field]


@dataclass
class CompanyPost:
    """
    처리 및 요약이 완료되어 데이터베이스에 저장될 최종 게시물 데이터를 나타냅니다.

    Attributes:
        title: 게시물의 제목.
        summary: LLM이 생성한 요약 또는 원본 콘텐츠의 일부.
        thumbnail_url: 게시물의 썸네일 URL (처리 후).
        field: 게시물의 기술 분야 (Field Enum, Optional).
        published_at: 게시물의 발행 일시.
        company: 게시물을 발행한 회사 (Company Enum).
        url: 게시물의 정규화된 URL.
        id: 데이터베이스에서의 게시물 ID (저장 후 할당됨, Optional).
    """

    title: str
    summary: str
    thumbnail_url: str
    field: Optional[Field]
    published_at: datetime
    company: Company
    url: str
    id: Optional[int] = None
