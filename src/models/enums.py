from enum import Enum

class Field(str, Enum):
    """기술 분야 열거형"""
    AI = "AI"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    DEVOPS = "DevOps"
    MOBILE = "Mobile"
    DB = "DB"
    COLLAB_TOOL = "Collab Tool"
    ETC = "기타"

class Company(str, Enum):
    """회사 열거형"""
    NAVER = "네이버"
    KAKAO = "카카오"
    LINE = "라인"
    TOSS = "토스"
    ETC = "기타"
