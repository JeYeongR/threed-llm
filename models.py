from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class Field(str, Enum):
    AI = "AI"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    DEVOPS = "DevOps"
    MOBILE = "Mobile"
    DB = "DB"
    COLLAB_TOOL = "Collab Tool"
    ETC = "기타"

class Company(str, Enum):
    NAVER = "네이버"
    KAKAO = "카카오"
    LINE = "라인"
    TOSS = "토스"
    ETC = "기타"

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
    field: Field
    published_at: datetime
    company: Company
    url: str
    id: Optional[int] = None
