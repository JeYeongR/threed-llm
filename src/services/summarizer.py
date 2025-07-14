import logging
from enum import Enum
from typing import Dict

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config.api_config import OPENAI_API_KEY, OPENAI_MODEL_NAME, OPENAI_TEMPERATURE

logger = logging.getLogger(__name__)


class SummaryField(str, Enum):
    AI = "AI"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    DEVOPS = "DevOps"
    MOBILE = "Mobile"
    DB = "DB"
    COLLAB_TOOL = "Collab Tool"
    ETC = "기타"


class SummaryResult(BaseModel):
    summary: str = Field(description="500-520자 사이의 요약 내용")
    field: SummaryField = Field(description="분류 카테고리")


FIELD_OPTIONS = ", ".join([field.value for field in SummaryField])

SYSTEM_PROMPT = f"""
당신은 한국어 요약을 생성하는 AI입니다.

다음 형식의 JSON만 반환하세요:
{{{{
  "summary": "요약 내용",
  "field": "분류"
}}}}

분류 종류:
{FIELD_OPTIONS}

분류 기준:
- AI: 인공지능, 머신러닝, LLM, ChatGPT, 생성형 AI 관련 내용
- DevOps: CI/CD, Docker, Kubernetes, AWS, Azure, GCP 등 클라우드 및 배포 관련 내용

내부 지침 (출력에 포함하지 마세요):
- 무조건 500-520자 사이의 요약 작성
- 500자 이하의 글이거나 500자 이상이라도 요약이 힘든 경우 500자 이하로 요약 작성
- 요약에 작성자의 이름이나 자기 소개를 절대 포함하지 마세요 (예: "저는", "필자는" 등)
- 요약은 내용에만 집중하고 작성자에 대한 언급은 모두 제거하세요
"""


def get_chat_client():
    return ChatOpenAI(
        model_name=OPENAI_MODEL_NAME,
        temperature=OPENAI_TEMPERATURE,
        openai_api_key=OPENAI_API_KEY,
    )


def summarize_content(content: str) -> Dict[str, str]:
    parser = PydanticOutputParser(pydantic_object=SummaryResult)

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", "다음 내용을 요약해주세요:\n{content}")]
    )

    chain = prompt | get_chat_client() | parser

    try:
        logger.info("콘텐츠 요약 시작")
        result = chain.invoke({"content": content})
        logger.info("콘텐츠 요약 완료")
        return result.dict()
    except Exception as e:
        logger.error(f"요약 중 오류 발생: {str(e)}")
        return {
            "summary": "요약을 생성하는 중 오류가 발생했습니다. 나중에 다시 시도해주세요.",
            "field": SummaryField.ETC.value,
        }
