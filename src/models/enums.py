from enum import Enum


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
    DEVOCEAN = "DEVOCEAN"
    ETC = "기타"
