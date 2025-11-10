"""PubMed/NCBI Entrez search client."""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from Bio import Entrez
import requests
from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PubMedArticle:
    """PubMed article metadata."""

    pmid: str
    doi: Optional[str]
    title: str
    abstract: str
    journal: str
    year: int
    authors: List[str]
    pmc_id: Optional[str] = None


class PubMedClient:
    """
    PubMed search client using NCBI Entrez API.

    Rate limits:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    """

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        tool_name: str = "tervyx-evidence",
    ):
        """
        Initialize PubMed client.

        Args:
            email: Required by NCBI
            api_key: Optional API key for higher rate limits
            tool_name: Tool identifier for NCBI
        """
        self.email = email
        self.api_key = api_key
        self.tool_name = tool_name

        Entrez.email = email
        Entrez.tool = tool_name
        if api_key:
            Entrez.api_key = api_key

        self.rate_limit = 10 if api_key else 3
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
        filters: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Search PubMed and return PMIDs.

        Args:
            query: Search query
            max_results: Maximum number of results
            filters: Additional filters (e.g., ["humans[MeSH Terms]"])

        Returns:
            List of PMIDs
        """
        self._throttle()

        # Build full query with filters
        full_query = query
        if filters:
            full_query = f"{query} AND {' AND '.join(filters)}"

        logger.info(f"PubMed search: {full_query} (max={max_results})")

        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=full_query,
                retmax=max_results,
                sort="relevance",
            )
            record = Entrez.read(handle)
            handle.close()

            pmids = record.get("IdList", [])
            logger.info(f"Found {len(pmids)} PMIDs")
            return pmids

        except Exception as e:
            logger.error(f"PubMed search failed: {e}")
            return []

    def fetch_details(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch article details for PMIDs.

        Args:
            pmids: List of PMIDs

        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []

        self._throttle()

        articles = []
        batch_size = 100

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            logger.info(f"Fetching details for {len(batch)} PMIDs...")

            try:
                handle = Entrez.efetch(
                    db="pubmed",
                    id=",".join(batch),
                    retmode="xml",
                )
                records = Entrez.read(handle)
                handle.close()

                for record in records["PubmedArticle"]:
                    article = self._parse_article(record)
                    if article:
                        articles.append(article)

            except Exception as e:
                logger.error(f"Failed to fetch batch: {e}")

        logger.info(f"Parsed {len(articles)} articles")
        return articles

    def _parse_article(self, record: Dict) -> Optional[PubMedArticle]:
        """Parse PubMed XML record into PubMedArticle."""
        try:
            medline = record["MedlineCitation"]
            article = medline["Article"]

            pmid = str(medline["PMID"])

            # DOI
            doi = None
            for article_id in record.get("PubmedData", {}).get("ArticleIdList", []):
                if article_id.attributes.get("IdType") == "doi":
                    doi = str(article_id)

            # Title
            title = str(article.get("ArticleTitle", ""))

            # Abstract
            abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
            if isinstance(abstract_parts, list):
                abstract = " ".join(str(part) for part in abstract_parts)
            else:
                abstract = str(abstract_parts)

            # Journal
            journal = str(article.get("Journal", {}).get("Title", ""))

            # Year
            pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            year = int(pub_date.get("Year", 0))

            # Authors
            authors = []
            for author in article.get("AuthorList", []):
                last_name = author.get("LastName", "")
                initials = author.get("Initials", "")
                if last_name:
                    authors.append(f"{last_name} {initials}".strip())

            # PMC ID
            pmc_id = None
            for article_id in record.get("PubmedData", {}).get("ArticleIdList", []):
                if article_id.attributes.get("IdType") == "pmc":
                    pmc_id = str(article_id)

            return PubMedArticle(
                pmid=pmid,
                doi=doi,
                title=title,
                abstract=abstract,
                journal=journal,
                year=year,
                authors=authors,
                pmc_id=pmc_id,
            )

        except Exception as e:
            logger.error(f"Failed to parse article: {e}")
            return None

    def search_and_fetch(
        self,
        query: str,
        max_results: int = 100,
        filters: Optional[List[str]] = None,
    ) -> List[PubMedArticle]:
        """
        Search and fetch in one call.

        Args:
            query: Search query
            max_results: Maximum results
            filters: Additional filters

        Returns:
            List of PubMedArticle objects
        """
        pmids = self.search(query, max_results, filters)
        return self.fetch_details(pmids)
