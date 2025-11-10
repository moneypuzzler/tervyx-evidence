"""K-Gate Pre-check: Safety signal detection."""

from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from src.common.io_utils import load_yaml
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class KPrecheckResult:
    """Result of K pre-check."""

    verdict: str  # "pass", "reject", "flag", "warn", "note"
    safety_signals: List[str]
    reason: str = ""
    references: List[str] = None

    def __post_init__(self):
        if self.references is None:
            self.references = []


class KPrecheck:
    """
    K-Gate Pre-screening.

    Scans for safety concerns BEFORE extraction to prioritize safety-focused searches.
    Full K-gate enforcement happens in A repo.
    """

    def __init__(self, config_path: Path | str):
        self.config = load_yaml(config_path)
        self.high_risk_substances = {
            item["name"]: item for item in self.config.get("high_risk_substances", [])
        }
        self.dose_thresholds = {
            item["substance"]: item for item in self.config.get("dose_thresholds", [])
        }
        self.interactions = self.config.get("interactions", [])
        self.contraindications = self.config.get("contraindications", [])
        self.regulatory_warnings = {
            item["substance"]: item for item in self.config.get("regulatory_warnings", [])
        }

    def check_entry(
        self,
        product: str,
        dose: str = None,
    ) -> KPrecheckResult:
        """
        Check product for safety signals.

        Args:
            product: Product name (e.g., "magnesium-glycinate", "ephedra")
            dose: Optional dosage string

        Returns:
            KPrecheckResult with verdict and safety signals
        """
        safety_signals = []
        verdict = "pass"
        reason = ""
        references = []

        # Normalize product name
        product_normalized = product.lower().replace("-", "_").replace(" ", "_")

        # Check high-risk substances
        for substance_name, substance_info in self.high_risk_substances.items():
            if substance_name in product_normalized:
                action = substance_info.get("action", "warn")
                reason_text = substance_info.get("reason", "")
                ref = substance_info.get("reference", "")

                safety_signals.append(f"High-risk substance: {substance_name}")
                references.append(ref)

                if action == "reject":
                    verdict = "reject"
                    reason = f"Prohibited substance: {reason_text}"
                    logger.warning(f"K-precheck REJECT: {product}. Reason: {reason}")
                    return KPrecheckResult(
                        verdict=verdict,
                        safety_signals=safety_signals,
                        reason=reason,
                        references=references,
                    )
                elif action in ["flag", "warn"] and verdict == "pass":
                    verdict = action
                    reason = reason_text

        # Check regulatory warnings
        for substance_name, warning_info in self.regulatory_warnings.items():
            if substance_name in product_normalized:
                action = warning_info.get("action", "flag")
                agency = warning_info.get("agency", "")
                warning_text = warning_info.get("warning", "")

                safety_signals.append(f"Regulatory warning ({agency}): {warning_text}")

                if action == "reject":
                    verdict = "reject"
                    reason = f"{agency} warning: {warning_text}"
                    return KPrecheckResult(
                        verdict=verdict,
                        safety_signals=safety_signals,
                        reason=reason,
                        references=references,
                    )

        # Check interactions
        for interaction in self.interactions:
            if interaction["supplement"] in product_normalized:
                severity = interaction.get("severity", "moderate")
                interacts = ", ".join(interaction.get("interacts_with", []))
                safety_signals.append(
                    f"Drug interaction ({severity}): {interaction['supplement']} with {interacts}"
                )

                if severity == "major" and verdict == "pass":
                    verdict = "flag"
                    reason = f"Major drug interaction with {interacts}"

        # If any signals but no rejection/flag, at least note
        if safety_signals and verdict == "pass":
            verdict = "note"

        if verdict != "pass":
            logger.info(f"K-precheck {verdict.upper()}: {product}. Signals: {len(safety_signals)}")

        return KPrecheckResult(
            verdict=verdict,
            safety_signals=safety_signals,
            reason=reason,
            references=references,
        )
