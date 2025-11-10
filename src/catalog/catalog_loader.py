"""Load and validate entry catalog."""

from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass
from src.common.io_utils import load_yaml


@dataclass
class EntryDefinition:
    """Single entry from catalog."""

    id: str
    intervention_type: str
    subcategory: str
    product: str
    outcome: str
    claim_text: str
    search_query: str
    version: str = "v1"
    max_studies: int = 5
    expected_effect_type: str = "SMD"
    expected_direction: str = "decrease"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], defaults: Dict[str, Any]) -> "EntryDefinition":
        """Create from catalog dict with defaults."""
        merged = {**defaults, **data}
        return cls(
            id=merged["id"],
            intervention_type=merged["intervention_type"],
            subcategory=merged["subcategory"],
            product=merged["product"],
            outcome=merged["outcome"],
            claim_text=merged["claim_text"],
            search_query=merged["search_query"],
            version=merged.get("version", "v1"),
            max_studies=merged.get("max_studies", 5),
            expected_effect_type=merged.get("expected_effect_type", "SMD"),
            expected_direction=merged.get("expected_direction", "decrease"),
        )

    def get_output_path(self, base_dir: Path) -> Path:
        """
        Get output directory path following convention:
        outputs/evidence_catalog/{intervention_type}/{subcategory}/{product}/{outcome}/v{version}/
        """
        return (
            Path(base_dir)
            / self.intervention_type
            / self.subcategory
            / self.product
            / self.outcome
            / self.version
        )


class CatalogLoader:
    """Load and manage entry catalog."""

    def __init__(self, catalog_path: Path | str):
        self.catalog_path = Path(catalog_path)
        self.catalog_data = load_yaml(self.catalog_path)
        self.defaults = self.catalog_data.get("defaults", {})
        self.entries: List[EntryDefinition] = []
        self._load_entries()

    def _load_entries(self) -> None:
        """Load entries from catalog."""
        entries_data = self.catalog_data.get("entries", [])
        for entry_data in entries_data:
            entry = EntryDefinition.from_dict(entry_data, self.defaults)
            self.entries.append(entry)

    def get_entry_by_id(self, entry_id: str) -> EntryDefinition | None:
        """Get entry by ID."""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def get_all_entries(self) -> List[EntryDefinition]:
        """Get all entries."""
        return self.entries

    def get_entries_by_intervention_type(self, intervention_type: str) -> List[EntryDefinition]:
        """Filter entries by intervention type."""
        return [e for e in self.entries if e.intervention_type == intervention_type]

    def get_entries_by_outcome(self, outcome: str) -> List[EntryDefinition]:
        """Filter entries by outcome."""
        return [e for e in self.entries if e.outcome == outcome]

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)
