"""Match papers to entries based on relevance."""

from typing import List, Dict, Any
from dataclasses import dataclass
from src.catalog.catalog_loader import EntryDefinition
from src.search.pubmed_client import PubMedArticle
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """Result of matching paper to entry."""

    pmid: str
    doi: str
    relevance_score: float
    intervention_match: float
    outcome_match: float
    design_match: float
    population_match: float
    matched: bool


class RelevanceMatcher:
    """
    Match papers to entry definitions based on relevance criteria.

    Uses simple keyword matching (can be enhanced with LLM later).
    """

    def __init__(self, relevance_threshold: float = 0.7):
        """
        Initialize matcher.

        Args:
            relevance_threshold: Minimum score to consider match (0-1)
        """
        self.relevance_threshold = relevance_threshold

    def match_papers(
        self,
        entry: EntryDefinition,
        papers: List[PubMedArticle],
    ) -> List[MatchResult]:
        """
        Match papers to entry and score relevance.

        Args:
            entry: Entry definition
            papers: List of candidate papers

        Returns:
            List of MatchResult, sorted by relevance score
        """
        results = []

        for paper in papers:
            result = self._score_paper(entry, paper)
            results.append(result)

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        matched_count = sum(1 for r in results if r.matched)
        logger.info(
            f"Matched {matched_count}/{len(results)} papers for entry {entry.id} "
            f"(threshold={self.relevance_threshold})"
        )

        return results

    def _score_paper(
        self,
        entry: EntryDefinition,
        paper: PubMedArticle,
    ) -> MatchResult:
        """
        Score individual paper against entry.

        Criteria (from extraction_policy.yaml):
        - intervention_match: 0.3
        - outcome_match: 0.3
        - design_match: 0.2
        - population_match: 0.2
        """
        # Prepare search text
        paper_text = f"{paper.title} {paper.abstract}".lower()

        # 1. Intervention match (0.3)
        intervention_keywords = self._extract_keywords(entry.product)
        intervention_match = self._keyword_overlap(intervention_keywords, paper_text)

        # 2. Outcome match (0.3)
        outcome_keywords = self._extract_keywords(entry.outcome)
        outcome_match = self._keyword_overlap(outcome_keywords, paper_text)

        # 3. Design match (0.2)
        design_keywords = ["randomized", "controlled trial", "rct", "placebo"]
        design_match = self._keyword_overlap(design_keywords, paper_text)

        # 4. Population match (0.2) - placeholder (would need more info)
        population_match = 0.5  # Default neutral

        # Weighted score
        relevance_score = (
            0.3 * intervention_match
            + 0.3 * outcome_match
            + 0.2 * design_match
            + 0.2 * population_match
        )

        matched = relevance_score >= self.relevance_threshold

        return MatchResult(
            pmid=paper.pmid,
            doi=paper.doi or "",
            relevance_score=relevance_score,
            intervention_match=intervention_match,
            outcome_match=outcome_match,
            design_match=design_match,
            population_match=population_match,
            matched=matched,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple: split by hyphens/underscores/spaces
        keywords = text.lower().replace("-", " ").replace("_", " ").split()
        return keywords

    def _keyword_overlap(self, keywords: List[str], text: str) -> float:
        """Compute keyword overlap score (0-1)."""
        if not keywords:
            return 0.0

        matches = sum(1 for kw in keywords if kw in text)
        return matches / len(keywords)
