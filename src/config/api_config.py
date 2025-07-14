import logging
import os
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    error_message = "OPENAI_API_KEY가 .env 파일에 제대로 설정되지 않았습니다. 프로그램을 종료합니다."
    logger.error(error_message)
    raise ValueError(error_message)

OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_MODEL_TEMPERATURE", 0.3))

logger.info(f"OpenAI 모델: {OPENAI_MODEL_NAME}, 온도: {OPENAI_TEMPERATURE}")
