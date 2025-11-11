"""
Gemini 2.5 Flash Lite client for evidence extraction.

CRITICAL: Temperature=0, extraction ONLY (no judgment/calculation).
"""

import os
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result from Gemini extraction."""

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    model: str = "gemini-2.5-flash-lite"
    temperature: float = 0.0
    timestamp: str = None
    tokens_used: Optional[int] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class GeminiExtractor:
    """
    Gemini 2.5 Flash Lite extractor for evidence.

    RULES:
    - temperature = 0 (MUST)
    - Extraction ONLY (no judgment, calculation, conversion)
    - JSON mode enforced
    - Audit logging for all calls
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash-lite",
        temperature: float = 0.0,
        max_retries: int = 3,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key (or use GEMINI_API_KEY env var)
            model: Model name (default: gemini-2.5-flash-lite)
            temperature: MUST be 0 for reproducibility
            max_retries: Max retry attempts
        """
        if genai is None:
            raise ImportError(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Set environment variable or pass api_key parameter."
            )

        self.model_name = model
        self.temperature = temperature
        self.max_retries = max_retries

        if temperature != 0:
            logger.warning(
                f"Temperature={temperature} != 0. "
                "For reproducibility, use temperature=0."
            )

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={
                "temperature": self.temperature,
                "top_p": 1.0,
                "top_k": 1,
                "max_output_tokens": 4096,
            }
        )

        logger.info(
            f"Initialized Gemini client: {self.model_name}, temp={self.temperature}"
        )

    def extract_from_abstract(
        self,
        abstract: str,
        study_id: str,
        doi: str,
        year: int,
        journal: str,
    ) -> ExtractionResult:
        """
        Extract structured evidence from abstract.

        Args:
            abstract: Full abstract text
            study_id: Study identifier
            doi: DOI
            year: Publication year
            journal: Journal name

        Returns:
            ExtractionResult with extracted data or error
        """
        prompt = self._build_extraction_prompt(
            abstract, study_id, doi, year, journal
        )

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Extracting {study_id} (attempt {attempt + 1}/{self.max_retries})"
                )

                response = self.model.generate_content(prompt)

                # Parse JSON from response
                try:
                    # Extract JSON from markdown code blocks if present
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif text.startswith("```"):
                        text = text.split("```")[1].split("```")[0].strip()

                    data = json.loads(text)

                    # Validate required fields
                    if not self._validate_extraction(data):
                        raise ValueError("Extraction failed validation")

                    logger.info(f"✓ Successfully extracted {study_id}")

                    # Safely extract token count (usage_metadata can be None)
                    tokens_used = None
                    if hasattr(response, 'usage_metadata') and response.usage_metadata is not None:
                        tokens_used = getattr(response.usage_metadata, 'total_token_count', None)

                    return ExtractionResult(
                        success=True,
                        data=data,
                        model=self.model_name,
                        temperature=self.temperature,
                        tokens_used=tokens_used,
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error for {study_id}: {e}")
                    logger.error(f"Response text: {response.text[:500]}")

                    if attempt == self.max_retries - 1:
                        return ExtractionResult(
                            success=False,
                            error=f"JSON parse error: {e}",
                        )

                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue

            except Exception as e:
                logger.error(f"Extraction error for {study_id}: {e}")

                if attempt == self.max_retries - 1:
                    return ExtractionResult(
                        success=False,
                        error=str(e),
                    )

                time.sleep(2 ** attempt)

        return ExtractionResult(
            success=False,
            error="Max retries exceeded",
        )

    def _build_extraction_prompt(
        self,
        abstract: str,
        study_id: str,
        doi: str,
        year: int,
        journal: str,
    ) -> str:
        """Build extraction prompt for Gemini."""

        return f"""You are a scientific data extraction assistant. Extract structured evidence from the research abstract below.

CRITICAL RULES:
1. COPY numbers EXACTLY as stated - NO calculation, conversion, or estimation
2. If information is not stated, use null
3. Return ONLY valid JSON (no markdown, no explanation)
4. Use precise quotes from abstract for narrative fields

Extract ALL of the following fields:

{{
  "study_id": "{study_id}",
  "doi": "{doi}",

  "outcome_context": {{
    "measure_name": "string (e.g., 'PSQI total score', 'Systolic blood pressure')",
    "measure_type": "validated_scale | objective_biomarker | self_report | clinical_event | physiological_measure | performance_test | other",
    "units": "string (e.g., 'points', 'mmHg', 'mg/dL')",
    "scale_range": "string or null (e.g., '0-21')",
    "direction": "decrease_is_benefit | increase_is_benefit | neutral | unclear",
    "assessment_method": "string (how it was measured)",
    "assessment_timing": "string (when measured)"
  }},

  "effect": {{
    "effect_type": "SMD | MD | OR | RR | HR | other",
    "effect_point": number,
    "ci_low": number,
    "ci_high": number,
    "p_value": "string (as stated, e.g., '<0.001', '0.042') or null",
    "baseline_mean_treatment": number or null,
    "baseline_mean_control": number or null,
    "absolute_change": number or null,
    "percent_change": number or null
  }},

  "clinical_context": {{
    "population": "string (target population)",
    "baseline_severity": "string (baseline characteristics)",
    "age_range": "string or null",
    "sex_distribution": "string or null",
    "intervention_description": "string (exact intervention with dose/duration)",
    "intervention_duration": "string",
    "control_description": "string",
    "setting": "string or null"
  }},

  "sample_sizes": {{
    "n_treatment": integer,
    "n_control": integer,
    "n_total": integer,
    "n_analyzed": integer or null
  }},

  "narrative": {{
    "author_effect_description": "string (how authors described effect)",
    "author_conclusion": "string (authors' conclusion)",
    "clinical_significance_claimed": boolean,
    "key_quotes": ["string", ...] (1-3 key sentences)
  }},

  "safety": {{
    "adverse_events_mentioned": boolean,
    "adverse_event_summary": "string or null",
    "safety_conclusion": "string or null"
  }},

  "quality_flags": {{
    "extraction_confidence": "high | medium | low",
    "data_source": "abstract_only",
    "needs_manual_review": boolean,
    "review_reason": "string or null"
  }}
}}

Abstract:
---
{abstract}
---

Study details:
- Study ID: {study_id}
- DOI: {doi}
- Year: {year}
- Journal: {journal}

Return ONLY the JSON object. No markdown, no explanation."""

    def _validate_extraction(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data has required fields."""

        required_top_level = ["outcome_context", "effect", "clinical_context", "sample_sizes"]

        for field in required_top_level:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False

        # Validate outcome_context
        if "measure_name" not in data["outcome_context"]:
            logger.error("Missing outcome_context.measure_name")
            return False

        # Validate effect
        effect_required = ["effect_point", "ci_low", "ci_high"]
        for field in effect_required:
            if field not in data["effect"]:
                logger.error(f"Missing effect.{field}")
                return False

        # Validate sample sizes
        if "n_treatment" not in data["sample_sizes"] or "n_control" not in data["sample_sizes"]:
            logger.error("Missing sample sizes")
            return False

        return True
