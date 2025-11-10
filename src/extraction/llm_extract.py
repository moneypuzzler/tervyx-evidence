"""LLM extraction (placeholder - requires API keys)."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedEvidence:
    """Extracted evidence from a single study."""

    study_id: str
    year: int
    design: str
    effect_type: str
    effect_point: float
    ci_low: float
    ci_high: float
    n_treat: int
    n_ctrl: int
    risk_of_bias: str
    doi: str
    journal_id: str
    outcome_measure: Optional[str] = None
    source_location: Optional[str] = None
    extraction_confidence: str = "medium"


class LLMExtractor:
    """
    LLM-based extraction engine.

    CRITICAL RULES:
    - temperature=0 (deterministic)
    - response_format=json_object (structured output)
    - COPY numbers exactly from paper - NO calculation/estimation
    - Log all prompts/responses for audit
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0,
        provider: str = "openai",
    ):
        """
        Initialize extractor.

        Args:
            model: Model name
            temperature: Temperature (MUST be 0 for reproducibility)
            provider: API provider (openai, anthropic, etc.)
        """
        self.model = model
        self.temperature = temperature
        self.provider = provider

        if temperature != 0:
            logger.warning(
                f"Temperature={temperature} != 0. For reproducibility, use temperature=0."
            )

    def extract_from_abstract(
        self,
        pmid: str,
        doi: str,
        title: str,
        abstract: str,
        journal: str,
        year: int,
    ) -> Optional[ExtractedEvidence]:
        """
        Extract evidence from abstract.

        NOTE: This is a PLACEHOLDER. Real implementation requires:
        1. OpenAI/Anthropic API client
        2. Structured prompt engineering
        3. JSON schema validation
        4. Retry logic with backoff
        5. Cost tracking

        For now, returns None (simulates "no extraction possible").
        """
        logger.warning(
            "LLM extraction not implemented (requires API keys). "
            "Returning None for PMID {pmid}."
        )

        # TODO: Implement real LLM extraction
        # Pseudo-code:
        #
        # prompt = build_extraction_prompt(title, abstract, schema)
        # response = call_llm_api(prompt, temperature=0, json_mode=True)
        # extracted = validate_and_parse(response)
        # return ExtractedEvidence(**extracted)

        return None

    def extract_from_full_text(
        self,
        pmid: str,
        doi: str,
        full_text: str,
        tables: Dict[str, Any],
        figures: Dict[str, Any],
    ) -> Optional[ExtractedEvidence]:
        """
        Extract evidence from full text + tables + figures.

        NOTE: PLACEHOLDER - not implemented yet.
        """
        logger.warning("Full-text extraction not implemented.")
        return None
