"""Export evidence to D repo (tervyx-entries) data catalog."""

import shutil
from pathlib import Path
from src.common.logging import get_logger

logger = get_logger(__name__)


class ExportToD:
    """
    Export evidence to D repo (pure data catalog).

    D repo is the "encyclopedia" - it stores ESV files for archival purposes.
    A repo will read from D and generate final artifacts.
    """

    def __init__(self, source_root: Path, target_root: Path):
        """
        Initialize exporter.

        Args:
            source_root: C repo outputs/evidence_catalog/
            target_root: D repo root directory
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
    ) -> bool:
        """
        Mirror entry to D repo.

        D repo structure mirrors C repo output structure.
        """
        # Source directory
        source_dir = (
            self.source_root / intervention_type / subcategory / product / outcome / version
        )

        if not source_dir.exists():
            logger.error(f"Source directory does not exist: {source_dir}")
            return False

        # Target directory (same structure in D)
        target_dir = (
            self.target_root / intervention_type / subcategory / product / outcome / version
        )

        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy all files
        for source_file in source_dir.iterdir():
            if source_file.is_file():
                shutil.copy2(source_file, target_dir / source_file.name)

        logger.info(f"Mirrored {source_dir.name} to D repo: {target_dir}")
        return True

    def export_all(self) -> int:
        """
        Mirror all entries to D repo.

        Returns:
            Number of entries exported
        """
        count = 0

        for evidence_csv in self.source_root.rglob("evidence.csv"):
            parts = evidence_csv.relative_to(self.source_root).parts

            if len(parts) < 6:
                logger.warning(f"Unexpected path structure: {evidence_csv}")
                continue

            intervention_type = parts[0]
            subcategory = parts[1]
            product = parts[2]
            outcome = parts[3]
            version = parts[4]

            success = self.export_entry(intervention_type, subcategory, product, outcome, version)

            if success:
                count += 1

        logger.info(f"Mirrored {count} entries to D repo")
        return count
