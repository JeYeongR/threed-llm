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
    DEVOCEAN = "데보션"
    TOSS = "토스"
    MY_REAL_TRIP = "마이리얼트립"
    LINE = "라인"
    ETC = "기타"
