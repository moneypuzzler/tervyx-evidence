"""Φ-Gate Pre-check: Physical/physiological plausibility screening."""

import re
from pathlib import Path
from typing import Dict, Any, Tuple
from dataclasses import dataclass
from src.common.io_utils import load_yaml
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PhiPrecheckResult:
    """Result of Φ pre-check."""

    verdict: str  # "pass", "reject", "warn"
    reason: str = ""
    matched_rule: str = ""


class PhiPrecheck:
    """
    Φ-Gate Pre-screening.

    Rejects obvious physical impossibilities BEFORE expensive search/extraction.
    Full Φ-gate enforcement happens in A repo.
    """

    def __init__(self, config_path: Path | str):
        self.config = load_yaml(config_path)
        self.hard_exclusions = self.config.get("hard_exclusions", [])
        self.route_checks = self.config.get("route_checks", {})
        self.category_requirements = self.config.get("category_requirements", {})

    def check_entry(
        self,
        intervention_type: str,
        product: str,
        outcome: str,
    ) -> PhiPrecheckResult:
        """
        Check if intervention-outcome pair passes Φ pre-screening.

        Args:
            intervention_type: e.g., "supplements", "device_noninvasive"
            product: e.g., "magnesium-glycinate", "magnetic-bracelet"
            outcome: e.g., "sleep", "cardiovascular"

        Returns:
            PhiPrecheckResult with verdict and reason
        """
        # Check hard exclusions
        for exclusion in self.hard_exclusions:
            intervention_pattern = exclusion.get("intervention_pattern", "")
            outcome_pattern = exclusion.get("outcome_pattern", "")
            action = exclusion.get("action", "warn")
            reason = exclusion.get("reason", "")

            # Build search string
            search_str = f"{intervention_type} {product}"

            if self._matches_pattern(search_str, intervention_pattern):
                if self._matches_pattern(outcome, outcome_pattern):
                    if action == "reject":
                        logger.warning(
                            f"Φ-precheck REJECT: {intervention_type}/{product} → {outcome}. Reason: {reason}"
                        )
                        return PhiPrecheckResult(
                            verdict="reject",
                            reason=reason,
                            matched_rule=f"{intervention_pattern} → {outcome_pattern}",
                        )
                    elif action == "warn":
                        logger.info(
                            f"Φ-precheck WARN: {intervention_type}/{product} → {outcome}. Reason: {reason}"
                        )
                        return PhiPrecheckResult(
                            verdict="warn",
                            reason=reason,
                            matched_rule=f"{intervention_pattern} → {outcome_pattern}",
                        )

        # If no exclusions matched, pass
        return PhiPrecheckResult(verdict="pass")

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches regex pattern."""
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            logger.error(f"Invalid regex pattern: {pattern}")
            return False

    def get_category_requirements(self, intervention_type: str) -> Dict[str, Any]:
        """Get requirements for intervention category."""
        return self.category_requirements.get(intervention_type, {})
