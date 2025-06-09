import logging
from typing import Dict, Literal

from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class SummaryResult(BaseModel):
    """요약 결과 모델"""

    summary: str = Field(description="500-520자 사이의 요약 내용")
    field: Literal[
        "AI", "Backend", "Frontend", "DevOps", "Mobile", "DB", "Collab Tool", "기타"
    ] = Field(description="분류 카테고리")


SYSTEM_PROMPT = """
당신은 한국어 요약을 생성하는 AI입니다.

다음 형식의 JSON만 반환하세요:
{{
  "summary": "요약 내용",
  "field": "분류"
}}

분류 종류:
AI, Backend, Frontend, DevOps, Mobile, DB, Collab Tool, 기타

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
    """ChatOpenAI 클라이언트를 생성하는 함수"""
    return ChatOpenAI(
        model_name="gpt-4o-mini", temperature=0.3, openai_api_key=OPENAI_API_KEY
    )


def summarize_content(content: str) -> Dict[str, str]:
    """
    주어진 콘텐츠를 요약하고 분류합니다.

    Args:
        content (str): 요약할 원본 텍스트

    Returns:
        dict: {"summary": 요약문, "field": 분류카테고리} 형식의 딕셔너리
    """
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
            "field": "기타",
        }
