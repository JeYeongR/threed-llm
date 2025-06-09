from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawledContentDto:

    title: str
    content: str
    url: str
    source_name: str
    thumbnail_url: str
    published_at: datetime


@dataclass
class LlmResponseDto:

    summary: str
    field: str


@dataclass
class CompanyPost:

    title: str
    summary: str
    thumbnail_url: str
    field: str
    published_at: datetime
    company: str
    url: str
    id: Optional[int] = None
