from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

from src.models.enums import Company, Field

Base = declarative_base()


class DBPost(Base):
    """
    모든 게시물의 기본 정보를 저장하는 'posts' 테이블의 SQLAlchemy 모델입니다.
    단일 테이블 상속의 기본 클래스 역할을 합니다.

    Attributes:
        id: 게시물의 고유 식별자 (PK, 자동 증가).
        title: 게시물의 제목 (최대 255자, nullable).
        content: 게시물의 요약된 내용 또는 본문 (Text, nullable).
        thumbnail_image_url: 썸네일 이미지의 URL (최대 255자, nullable).
        field: 게시물의 기술 분야 (Field Enum, nullable).
        published_at: 게시물이 발행된 날짜 및 시간 (nullable).
        created_at: 레코드가 생성된 날짜 및 시간 (non-nullable).
        updated_at: 레코드가 마지막으로 수정된 날짜 및 시간 (non-nullable).
        view_count: 게시물 조회수 (기본값 0, non-nullable).
        post_type: 게시물의 유형을 구분하는 문자열 (상속에 사용됨, non-nullable).
    """

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    thumbnail_image_url = Column(String(255), nullable=True)
    field = Column(Enum(Field), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    view_count = Column(Integer, nullable=False, default=0)
    post_type = Column(String(31), nullable=False)

    __mapper_args__ = {"polymorphic_on": post_type, "polymorphic_identity": "POST"}


class DBCompanyPost(DBPost):
    """
    회사 기술 블로그 게시물의 추가 정보를 나타내는 SQLAlchemy 모델입니다.
    'posts' 테이블을 사용하며, DBPost를 상속받습니다.

    Attributes:
        id: 'posts' 테이블의 id를 참조하는 외래 키 (PK).
        source_url: 게시물의 원본 URL (최대 255자, nullable).
        company: 게시물을 발행한 회사 (Company Enum, non-nullable).
    """

    __tablename__ = "company_posts"

    id = Column(Integer, ForeignKey("posts.id"), primary_key=True)
    source_url = Column(String(255), nullable=True)
    company = Column(Enum(Company), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "COMPANY"}
