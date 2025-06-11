"""
애플리케이션에서 사용되는 주요 Enum 클래스들을 정의합니다.

이 모듈은 게시물의 기술 분야(Field) 및 회사(Company)를 나타내는
Enum 타입을 제공합니다.
"""

from enum import Enum


class Field(str, Enum):
    """게시물의 기술 분야를 나타내는 Enum 클래스입니다."""

    AI = "AI"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    DEVOPS = "DevOps"
    MOBILE = "Mobile"
    DB = "DB"
    COLLAB_TOOL = "Collab Tool"
    ETC = "기타"


class Company(str, Enum):
    """회사를 나타내는 Enum 클래스입니다."""

    NAVER = "네이버"
    KAKAO = "카카오"
    DEVOCEAN = "데보션"
    TOSS = "토스"
    MY_REAL_TRIP = "마이리얼트립"
    LINE = "라인"
    DAANGN = "당근"
    OLIVE_YOUNG = "올리브영"
    ETC = "기타"
