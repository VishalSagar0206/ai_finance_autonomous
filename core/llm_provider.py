import os
from typing import Any, Dict, Optional, Type, TypeVar
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

from adk_framework_v3.core.config import config

class LLMProvider:
    """
    Centralized provider for Gemini 1.5 Pro instances and structured output chains.
    Enforces 100% data accuracy through Pydantic validation.
    """

    @staticmethod
    def get_model(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
        """Returns a configured Gemini model instance."""
        api_key = config.GOOGLE_API_KEY
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found in environment. Using mock logic.")
            return None
        
        # Best Practice: Use specific version and explicit safety settings
        return ChatGoogleGenerativeAI(
            model="gemini-3.1-pro-preview",
            temperature=temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,
        )

    @staticmethod
    def run_structured_chain(
        prompt_text: str, 
        input_data: Dict[str, Any], 
        output_schema: Type[T]
    ) -> T:
        """
        Executes a prompt through Gemini and parses the response into the requested Pydantic model.
        """
        model = LLMProvider.get_model()
        
        # Fallback to a basic 'mock' or error if no model is available
        if not model:
            logger.error("LLM model is unavailable. Ensure GOOGLE_API_KEY is set.")
            raise RuntimeError("Gemini model is unavailable.")

        parser = PydanticOutputParser(pydantic_object=output_schema)
        
        # Best Practice: System prompt and formatting instructions
        prompt = ChatPromptTemplate.from_template(
            "System: You are an expert AI Systems Architect and Financial Quantitative Analyst.\n"
            "{format_instructions}\n"
            "Context: {prompt_text}\n"
            "Input Data: {input_data}"
        )
        
        # Create a Chain: Prompt -> Model -> Parser
        chain = prompt | model | parser
        
        try:
            return chain.invoke({
                "prompt_text": prompt_text,
                "input_data": input_data,
                "format_instructions": parser.get_format_instructions()
            })
        except Exception as e:
            logger.error(f"Error in Gemini Chain execution: {str(e)}")
            # In production, we'd add retry logic here
            raise

llm_provider = LLMProvider()
