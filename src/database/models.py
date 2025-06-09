from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

from src.models.enums import Company, Field

Base = declarative_base()

class DBPost(Base):
    """데이터베이스 포스트 모델"""
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
    
    __mapper_args__ = {
        'polymorphic_on': post_type,
        'polymorphic_identity': 'POST'
    }

class DBCompanyPost(DBPost):
    """데이터베이스 회사 포스트 모델"""
    __tablename__ = "company_posts"
    
    id = Column(Integer, ForeignKey("posts.id"), primary_key=True)
    source_url = Column(String(255), nullable=True)
    company = Column(Enum(Company), nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'COMPANY'
    }
