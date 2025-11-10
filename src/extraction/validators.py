"""Validation logic for extracted evidence."""

from typing import Dict, Any, List, Tuple
from src.common.logging import get_logger

logger = get_logger(__name__)


class EvidenceValidator:
    """Validate extracted evidence for integrity and consistency."""

    @staticmethod
    def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate single evidence record.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Required fields
        required = [
            "study_id",
            "year",
            "design",
            "effect_type",
            "effect_point",
            "ci_low",
            "ci_high",
            "n_treat",
            "n_ctrl",
            "risk_of_bias",
            "doi",
            "journal_id",
        ]

        for field in required:
            if field not in record or record[field] is None:
                errors.append(f"Missing required field: {field}")

        if errors:
            return False, errors

        # Type checks
        try:
            year = int(record["year"])
            if not (1990 <= year <= 2025):
                errors.append(f"Year out of range: {year}")
        except (ValueError, TypeError):
            errors.append(f"Invalid year: {record['year']}")

        try:
            effect_point = float(record["effect_point"])
            ci_low = float(record["ci_low"])
            ci_high = float(record["ci_high"])

            # CI order check (for positive effects)
            # Note: For negative effects, order might be reversed
            # This is a simplified check
            if not (ci_low <= ci_high):
                logger.warning(
                    f"CI order unusual: ci_low={ci_low}, ci_high={ci_high}. "
                    "Check if effect is negative."
                )

        except (ValueError, TypeError) as e:
            errors.append(f"Invalid numeric values: {e}")

        try:
            n_treat = int(record["n_treat"])
            n_ctrl = int(record["n_ctrl"])

            if n_treat <= 0:
                errors.append(f"n_treat must be > 0, got {n_treat}")
            if n_ctrl <= 0:
                errors.append(f"n_ctrl must be > 0, got {n_ctrl}")

        except (ValueError, TypeError) as e:
            errors.append(f"Invalid sample sizes: {e}")

        # Effect type
        valid_effect_types = ["SMD", "MD", "OR", "RR", "HR"]
        if record["effect_type"] not in valid_effect_types:
            errors.append(f"Invalid effect_type: {record['effect_type']}")

        # Risk of bias
        valid_rob = ["low", "moderate", "high", "unclear"]
        if record["risk_of_bias"] not in valid_rob:
            errors.append(f"Invalid risk_of_bias: {record['risk_of_bias']}")

        # DOI format (basic check)
        doi = record["doi"]
        if not doi.startswith("10."):
            errors.append(f"Invalid DOI format: {doi}")

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def validate_dataframe(df) -> Tuple[bool, Dict[int, List[str]]]:
        """
        Validate entire DataFrame.

        Returns:
            (all_valid, {row_index: [errors]})
        """
        import pandas as pd

        all_errors = {}

        for idx, row in df.iterrows():
            record = row.to_dict()
            is_valid, errors = EvidenceValidator.validate_record(record)
            if not is_valid:
                all_errors[idx] = errors

        all_valid = len(all_errors) == 0

        if not all_valid:
            logger.error(f"Validation failed for {len(all_errors)} records")

        return all_valid, all_errors
