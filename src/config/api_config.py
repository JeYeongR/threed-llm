import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
    raise ValueError("OPENAI_API_KEY가 .env 파일에 제대로 설정되지 않았습니다.")

OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
OPENAI_MODEL_TEMPERATURE = float(os.getenv("OPENAI_MODEL_TEMPERATURE", 0.3))
