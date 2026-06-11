from typing import Any, Dict, Type, TypeVar
import logging

from pydantic import BaseModel

from core.config import config

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

try:  # Optional: only needed in live mode.
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import PydanticOutputParser
except Exception:  # pragma: no cover - depends on optional environment packages
    ChatGoogleGenerativeAI = None
    ChatPromptTemplate = None
    PydanticOutputParser = None


class LLMProvider:
    """
    Centralized provider for Gemini-backed structured chains.

    The rest of the project can import this module even when LangChain/Gemini
    packages are not installed. Agent modules use deterministic fallbacks unless
    ADK_LIVE_MODE=1 and a real GOOGLE_API_KEY are configured.
    """

    @staticmethod
    def get_model(temperature: float = 0.0):
        """Return a configured Gemini model instance, or None in offline mode."""
        if not config.has_live_llm():
            logger.info("Live LLM disabled; using deterministic agent fallbacks.")
            return None

        if ChatGoogleGenerativeAI is None:
            logger.warning("LangChain Gemini dependencies are not installed; using fallback logic.")
            return None

        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=temperature,
            google_api_key=config.GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )

    @staticmethod
    def run_structured_chain(
        prompt_text: str, input_data: Dict[str, Any], output_schema: Type[T]
    ) -> T:
        """Execute a structured Gemini chain and parse to a Pydantic model."""
        model = LLMProvider.get_model()
        if not model:
            raise RuntimeError("Live Gemini model is unavailable; fallback mode is active.")

        if ChatPromptTemplate is None or PydanticOutputParser is None:
            raise RuntimeError("LangChain structured-output dependencies are unavailable.")

        parser = PydanticOutputParser(pydantic_object=output_schema)
        prompt = ChatPromptTemplate.from_template(
            "System: You are an expert AI Systems Architect and Financial Quantitative Analyst.\n"
            "{format_instructions}\n"
            "Context: {prompt_text}\n"
            "Input Data: {input_data}"
        )
        chain = prompt | model | parser
        try:
            return chain.invoke(
                {
                    "prompt_text": prompt_text,
                    "input_data": input_data,
                    "format_instructions": parser.get_format_instructions(),
                }
            )
        except Exception as exc:
            logger.error("Error in Gemini chain execution: %s", exc)
            raise


llm_provider = LLMProvider()
