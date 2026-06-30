from __future__ import annotations

from typing import TypeVar

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.use_llm and self.settings.openai_api_key)

    def structured(self, prompt: ChatPromptTemplate, schema: type[T], payload: dict, fallback: T) -> tuple[T, dict]:
        if not self.enabled:
            return fallback, {}
        try:
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(
                model=self.settings.llm_model,
                api_key=self.settings.openai_api_key,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=self.settings.llm_max_retries,
            ).with_structured_output(schema)
            result = (prompt | model).invoke(payload)
            usage = {}
            return result, usage
        except Exception:
            return fallback, {}

    def text(self, prompt: ChatPromptTemplate, payload: dict, fallback: str) -> tuple[str, dict]:
        if not self.enabled:
            return fallback, {}
        try:
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(
                model=self.settings.llm_model,
                api_key=self.settings.openai_api_key,
                timeout=self.settings.llm_timeout_seconds,
                max_retries=self.settings.llm_max_retries,
            )
            result = (prompt | model).invoke(payload)
            return str(result.content), {}
        except Exception:
            return fallback, {}
