"""Crossref API client (supplementary to PubMed)."""

import time
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CrossrefArticle:
    """Crossref article metadata."""

    doi: str
    title: str
    abstract: Optional[str]
    journal: str
    year: int
    authors: List[str]


class CrossrefClient:
    """
    Crossref API client for supplementary searches.

    Uses "polite pool" with 50 requests/second.
    """

    def __init__(self, mailto: str):
        """
        Initialize Crossref client.

        Args:
            mailto: Email for polite pool access
        """
        self.mailto = mailto
        self.base_url = "https://api.crossref.org/works"
        self.rate_limit = 50
        self.last_request_time = 0

    def _throttle(self):
        """Respect rate limits."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    def search(
        self,
        query: str,
        max_results: int = 100,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[CrossrefArticle]:
        """
        Search Crossref.

        Args:
            query: Search query
            max_results: Maximum results
            filters: Optional filters (e.g., {"type": "journal-article"})

        Returns:
            List of CrossrefArticle objects
        """
        self._throttle()

        params = {
            "query": query,
            "rows": min(max_results, 1000),
            "mailto": self.mailto,
        }

        if filters:
            for key, value in filters.items():
                params[f"filter"] = f"{key}:{value}"

        logger.info(f"Crossref search: {query} (max={max_results})")

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get("message", {}).get("items", []):
                article = self._parse_item(item)
                if article:
                    articles.append(article)

            logger.info(f"Found {len(articles)} Crossref articles")
            return articles

        except Exception as e:
            logger.error(f"Crossref search failed: {e}")
            return []

    def _parse_item(self, item: Dict) -> Optional[CrossrefArticle]:
        """Parse Crossref item into CrossrefArticle."""
        try:
            doi = item.get("DOI")
            if not doi:
                return None

            # Title
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""

            # Abstract
            abstract = item.get("abstract", None)

            # Journal
            container_list = item.get("container-title", [])
            journal = container_list[0] if container_list else ""

            # Year
            pub_date = item.get("published-print", item.get("published-online", {}))
            date_parts = pub_date.get("date-parts", [[]])[0]
            year = date_parts[0] if date_parts else 0

            # Authors
            authors = []
            for author in item.get("author", []):
                family = author.get("family", "")
                given = author.get("given", "")
                if family:
                    authors.append(f"{family} {given}".strip())

            return CrossrefArticle(
                doi=doi,
                title=title,
                abstract=abstract,
                journal=journal,
                year=year,
                authors=authors,
            )

        except Exception as e:
            logger.error(f"Failed to parse Crossref item: {e}")
            return None
