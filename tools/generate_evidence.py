#!/usr/bin/env python3
"""
Generate evidence for a single entry (main C repo pipeline).

Usage:
    python tools/generate_evidence.py \
        --entry-id SLP-MG-GLY-PSQI \
        --catalog config/entry_catalog.yaml \
        --output outputs/evidence_catalog
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.catalog.catalog_loader import CatalogLoader
from src.gates_precheck.phi_precheck import PhiPrecheck
from src.gates_precheck.k_precheck import KPrecheck
from src.search.pubmed_client import PubMedClient
from src.matching.relevance_matcher import RelevanceMatcher
from src.extraction.llm_extract import LLMExtractor
from src.extraction.validators import EvidenceValidator
from src.common.io_utils import save_json, save_evidence_csv, ensure_dir
from src.common.hashing import compute_manifest_hashes
from src.common.logging import setup_logger
import os

logger = setup_logger("generate_evidence")


def main():
    parser = argparse.ArgumentParser(description="Generate evidence for single entry")
    parser.add_argument("--entry-id", required=True, help="Entry ID from catalog")
    parser.add_argument(
        "--catalog",
        default="config/entry_catalog.yaml",
        help="Path to entry catalog",
    )
    parser.add_argument(
        "--output",
        default="outputs/evidence_catalog",
        help="Output directory",
    )
    parser.add_argument(
        "--phi-config",
        default="config/phi_precheck.yaml",
        help="Φ-gate config",
    )
    parser.add_argument(
        "--k-config",
        default="config/k_precheck.yaml",
        help="K-gate config",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("TERVYX_EMAIL", "research@example.com"),
        help="Email for PubMed API",
    )
    parser.add_argument(
        "--ncbi-api-key",
        default=os.getenv("NCBI_API_KEY"),
        help="NCBI API key (optional)",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=50,
        help="Max papers to search",
    )
    parser.add_argument(
        "--relevance-threshold",
        type=float,
        default=0.7,
        help="Relevance matching threshold",
    )

    args = parser.parse_args()

    # Load catalog
    logger.info(f"Loading catalog: {args.catalog}")
    catalog = CatalogLoader(args.catalog)
    entry = catalog.get_entry_by_id(args.entry_id)

    if not entry:
        logger.error(f"Entry not found: {args.entry_id}")
        return 1

    logger.info(f"Processing entry: {entry.id} ({entry.claim_text})")

    # Output directory
    output_dir = entry.get_output_path(Path(args.output))
    ensure_dir(output_dir)
    logger.info(f"Output directory: {output_dir}")

    # ========================================================================
    # STEP 1: Φ-Gate Pre-check
    # ========================================================================
    logger.info("Step 1: Φ-Gate pre-check...")
    phi_checker = PhiPrecheck(args.phi_config)
    phi_result = phi_checker.check_entry(
        entry.intervention_type,
        entry.product,
        entry.outcome,
    )

    if phi_result.verdict == "reject":
        logger.error(f"Φ-gate REJECT: {phi_result.reason}")
        # Save rejection metadata
        metadata = {
            "entry_id": entry.id,
            "status": "phi_rejected",
            "reason": phi_result.reason,
            "matched_rule": phi_result.matched_rule,
            "timestamp": datetime.now().isoformat(),
        }
        save_json(metadata, output_dir / "metadata.json")
        return 1

    logger.info(f"Φ-gate: {phi_result.verdict}")

    # ========================================================================
    # STEP 2: K-Gate Pre-check
    # ========================================================================
    logger.info("Step 2: K-Gate pre-check...")
    k_checker = KPrecheck(args.k_config)
    k_result = k_checker.check_entry(entry.product)

    if k_result.verdict == "reject":
        logger.error(f"K-gate REJECT: {k_result.reason}")
        metadata = {
            "entry_id": entry.id,
            "status": "k_rejected",
            "reason": k_result.reason,
            "safety_signals": k_result.safety_signals,
            "timestamp": datetime.now().isoformat(),
        }
        save_json(metadata, output_dir / "metadata.json")
        return 1

    logger.info(f"K-gate: {k_result.verdict} ({len(k_result.safety_signals)} signals)")

    # ========================================================================
    # STEP 3: Search PubMed
    # ========================================================================
    logger.info("Step 3: Searching PubMed...")
    pubmed = PubMedClient(
        email=args.email,
        api_key=args.ncbi_api_key,
    )

    # Search with RCT filter
    filters = ["randomized controlled trial[pt]", "humans[MeSH Terms]", "english[Language]"]
    papers = pubmed.search_and_fetch(
        query=entry.search_query,
        max_results=args.max_papers,
        filters=filters,
    )

    logger.info(f"Found {len(papers)} papers")

    if not papers:
        logger.warning("No papers found - cannot generate evidence")
        metadata = {
            "entry_id": entry.id,
            "status": "no_papers_found",
            "search_query": entry.search_query,
            "timestamp": datetime.now().isoformat(),
        }
        save_json(metadata, output_dir / "metadata.json")
        return 0

    # ========================================================================
    # STEP 4: Match papers to entry
    # ========================================================================
    logger.info("Step 4: Matching papers to entry...")
    matcher = RelevanceMatcher(relevance_threshold=args.relevance_threshold)
    match_results = matcher.match_papers(entry, papers)

    matched_papers = [r for r in match_results if r.matched]
    logger.info(f"Matched {len(matched_papers)} papers")

    if not matched_papers:
        logger.warning("No papers matched - cannot generate evidence")
        metadata = {
            "entry_id": entry.id,
            "status": "no_matches",
            "n_candidates": len(papers),
            "relevance_threshold": args.relevance_threshold,
            "timestamp": datetime.now().isoformat(),
        }
        save_json(metadata, output_dir / "metadata.json")
        return 0

    # ========================================================================
    # STEP 5: Extract evidence (PLACEHOLDER)
    # ========================================================================
    logger.info("Step 5: Extracting evidence...")
    logger.warning("LLM extraction not implemented - generating MOCK data for demonstration")

    # MOCK: Generate placeholder evidence.csv
    records = []
    for i, match in enumerate(matched_papers[: entry.max_studies]):
        # Find corresponding paper
        paper = next(p for p in papers if p.pmid == match.pmid)

        # MOCK DATA - in real implementation, this would come from LLM extraction
        records.append(
            {
                "study_id": f"{paper.authors[0].split()[0] if paper.authors else 'Unknown'}{paper.year}",
                "year": paper.year,
                "design": "randomized controlled trial",
                "effect_type": entry.expected_effect_type,
                "effect_point": -0.5 - (i * 0.1),  # MOCK
                "ci_low": -0.8 - (i * 0.1),  # MOCK
                "ci_high": -0.2 - (i * 0.1),  # MOCK
                "n_treat": 30 + (i * 5),  # MOCK
                "n_ctrl": 30 + (i * 5),  # MOCK
                "risk_of_bias": "moderate",
                "doi": paper.doi or f"10.MOCK/{paper.pmid}",
                "journal_id": paper.journal[:20] if paper.journal else "Unknown",
                "outcome_measure": entry.outcome,
                "source_location": "Abstract (MOCK)",
                "extraction_confidence": "low",  # MOCK data!
            }
        )

    df = pd.DataFrame(records)

    # ========================================================================
    # STEP 6: Validate
    # ========================================================================
    logger.info("Step 6: Validating evidence...")
    is_valid, errors = EvidenceValidator.validate_dataframe(df)

    if not is_valid:
        logger.error(f"Validation failed: {errors}")
        return 1

    logger.info("Validation passed")

    # ========================================================================
    # STEP 7: Save outputs
    # ========================================================================
    logger.info("Step 7: Saving outputs...")

    # evidence.csv
    save_evidence_csv(df, output_dir / "evidence.csv")
    logger.info(f"Saved evidence.csv ({len(df)} records)")

    # metadata.json
    metadata = {
        "entry_id": entry.id,
        "intervention_type": entry.intervention_type,
        "subcategory": entry.subcategory,
        "product": entry.product,
        "outcome": entry.outcome,
        "version": entry.version,
        "catalog_id": entry.id,
        "n_candidates_scanned": len(papers),
        "n_studies_included": len(df),
        "llm_models": ["MOCK - not implemented"],
        "created": datetime.now().isoformat(),
        "phi_verdict": phi_result.verdict,
        "k_verdict": k_result.verdict,
        "k_safety_signals": k_result.safety_signals,
    }
    save_json(metadata, output_dir / "metadata.json")

    # extraction_log.json (simplified)
    extraction_log = [
        {
            "doi": rec["doi"],
            "study_id": rec["study_id"],
            "verdict": "mock_extraction",
            "note": "MOCK data - real LLM extraction not implemented",
        }
        for rec in records
    ]
    save_json(extraction_log, output_dir / "extraction_log.json")

    # manifest.json
    manifest = {
        "files": compute_manifest_hashes(output_dir),
        "policy_anchor_hint": "A will compute policy_fingerprint later",
        "created": datetime.now().isoformat(),
    }
    save_json(manifest, output_dir / "manifest.json")

    logger.info("✓ Evidence generation complete")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Studies: {len(df)}")
    logger.info("  NOTE: Evidence contains MOCK data - LLM extraction not implemented")

    return 0


if __name__ == "__main__":
    sys.exit(main())
