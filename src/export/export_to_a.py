"""Export evidence to A repo (tervyx) for deterministic build."""

import shutil
from pathlib import Path
from typing import Optional
from src.common.logging import get_logger

logger = get_logger(__name__)


class ExportToA:
    """
    Export evidence.csv to A repo for consumption by deterministic pipeline.

    A repo expects:
    entries/{intervention_type}/{subcategory}/{product}/{outcome}/v{version}/evidence.csv
    """

    def __init__(self, source_root: Path, target_root: Path):
        """
        Initialize exporter.

        Args:
            source_root: C repo outputs/evidence_catalog/
            target_root: A repo entries/ directory
        """
        self.source_root = Path(source_root)
        self.target_root = Path(target_root)

    def export_entry(
        self,
        intervention_type: str,
        subcategory: str,
        product: str,
        outcome: str,
        version: str = "v1",
        copy_mode: str = "sync",
    ) -> bool:
        """
        Export single entry to A repo.

        Args:
            intervention_type, subcategory, product, outcome, version: Entry identifiers
            copy_mode: "sync" (copy all files) or "evidence_only" (just evidence.csv)

        Returns:
            True if successful
        """
        # Source directory
        source_dir = (
            self.source_root / intervention_type / subcategory / product / outcome / version
        )

        if not source_dir.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return False

        # Target directory
        target_dir = (
            self.target_root / intervention_type / subcategory / product / outcome / version
        )

        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy evidence.csv (mandatory)
        evidence_csv = source_dir / "evidence.csv"
        if not evidence_csv.exists():
            logger.error(f"evidence.csv not found: {evidence_csv}")
            return False

        shutil.copy2(evidence_csv, target_dir / "evidence.csv")
        logger.info(f"Copied evidence.csv to {target_dir}")

        # Copy metadata (optional but recommended)
        if copy_mode == "sync":
            for filename in ["metadata.json", "extraction_log.json", "manifest.json"]:
                source_file = source_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, target_dir / filename)
                    logger.info(f"Copied {filename} to {target_dir}")

        return True

    def export_all(self, copy_mode: str = "sync") -> int:
        """
        Export all entries found in source_root to target_root.

        Returns:
            Number of entries exported
        """
        count = 0

        # Walk source directory
        for evidence_csv in self.source_root.rglob("evidence.csv"):
            # Parse path: .../{intervention_type}/{subcategory}/{product}/{outcome}/{version}/evidence.csv
            parts = evidence_csv.relative_to(self.source_root).parts

            if len(parts) < 6:
                logger.warning(f"Unexpected path structure: {evidence_csv}")
                continue

            intervention_type = parts[0]
            subcategory = parts[1]
            product = parts[2]
            outcome = parts[3]
            version = parts[4]

            success = self.export_entry(
                intervention_type, subcategory, product, outcome, version, copy_mode
            )

            if success:
                count += 1

        logger.info(f"Exported {count} entries to A repo")
        return count
