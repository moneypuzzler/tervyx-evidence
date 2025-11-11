#!/usr/bin/env python3
"""
Run 30-sample extraction test with Gemini 2.5 Flash Lite.

Usage:
    export GEMINI_API_KEY=your_key
    export NCBI_API_KEY=your_key  # optional
    export TERVYX_EMAIL=your@email.com

    python tools/run_30_sample_extraction.py --limit 30
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.search.pubmed_client import PubMedClient
from src.extraction.gemini_client import GeminiExtractor
from src.catalog.catalog_loader import CatalogLoader
from src.common.logging import setup_logger
from src.common.io_utils import save_json, ensure_dir

logger = setup_logger("sample_extraction", level="INFO")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run 30-sample extraction test")
    parser.add_argument("--limit", type=int, default=30, help="Number of samples to extract")
    parser.add_argument(
        "--catalog", default="config/entry_catalog.yaml", help="Entry catalog path"
    )
    parser.add_argument(
        "--output", default="extractions/sleep", help="Output directory"
    )
    parser.add_argument(
        "--abstracts-out", default="abstracts/sleep", help="Abstracts output directory"
    )
    parser.add_argument(
        "--email", default=os.getenv("TERVYX_EMAIL", "research@example.com")
    )
    parser.add_argument("--ncbi-api-key", default=os.getenv("NCBI_API_KEY"))
    parser.add_argument("--gemini-api-key", default=os.getenv("GEMINI_API_KEY"))

    args = parser.parse_args()

    if not args.gemini_api_key:
        logger.error("GEMINI_API_KEY not set. Export GEMINI_API_KEY=your_key")
        return 1

    # Create output directories
    ensure_dir(args.output)
    ensure_dir(args.abstracts_out)

    logger.info("=" * 60)
    logger.info("TERVYX 30-SAMPLE EXTRACTION TEST")
    logger.info("=" * 60)
    logger.info(f"Model: gemini-2.5-flash-lite")
    logger.info(f"Temperature: 0")
    logger.info(f"Target samples: {args.limit}")

    # ========================================================================
    # STEP 1: Load catalog and select entries
    # ========================================================================
    logger.info("\nStep 1: Loading entry catalog...")
    catalog = CatalogLoader(args.catalog)

    # Focus on sleep entries for test
    sleep_entries = [e for e in catalog.get_all_entries() if e.outcome == "sleep"]
    logger.info(f"Found {len(sleep_entries)} sleep entries")

    if not sleep_entries:
        logger.error("No sleep entries found in catalog")
        return 1

    # ========================================================================
    # STEP 2: Search PubMed for abstracts
    # ========================================================================
    logger.info("\nStep 2: Searching PubMed...")
    pubmed = PubMedClient(email=args.email, api_key=args.ncbi_api_key)

    all_papers = []
    papers_per_entry = max(1, args.limit // len(sleep_entries))

    for entry in sleep_entries[:3]:  # Use first 3 entries to get variety
        logger.info(f"  Searching: {entry.id} - {entry.search_query}")

        filters = [
            "randomized controlled trial[pt]",
            "humans[MeSH Terms]",
            "english[Language]",
        ]

        papers = pubmed.search_and_fetch(
            query=entry.search_query,
            max_results=papers_per_entry,
            filters=filters,
        )

        logger.info(f"    Found {len(papers)} papers")
        all_papers.extend(papers)

        if len(all_papers) >= args.limit:
            break

        time.sleep(0.5)  # Be nice to NCBI

    all_papers = all_papers[: args.limit]
    logger.info(f"\nTotal papers collected: {len(all_papers)}")

    if not all_papers:
        logger.error("No papers found. Check search queries.")
        return 1

    # ========================================================================
    # STEP 3: Save abstracts
    # ========================================================================
    logger.info("\nStep 3: Saving abstracts...")

    abstracts_index = []
    for paper in all_papers:
        abstracts_index.append(
            {
                "study_id": f"{paper.authors[0].split()[0] if paper.authors else 'Unknown'}{paper.year}",
                "pmid": paper.pmid,
                "doi": paper.doi or f"PMID:{paper.pmid}",
                "year": paper.year,
                "journal": paper.journal,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": "; ".join(paper.authors[:5]),
                "pmc_id": paper.pmc_id,
            }
        )

    abstracts_df = pd.DataFrame(abstracts_index)
    abstracts_file = Path(args.abstracts_out) / "abstracts_sample_30.csv"
    abstracts_df.to_csv(abstracts_file, index=False)
    logger.info(f"Saved {len(abstracts_df)} abstracts to {abstracts_file}")

    # ========================================================================
    # STEP 4: Extract with Gemini
    # ========================================================================
    logger.info("\nStep 4: Extracting with Gemini 2.5 Flash Lite...")
    logger.info("⚠️  This will use Gemini API tokens")

    gemini = GeminiExtractor(
        api_key=args.gemini_api_key,
        model="gemini-2.5-flash-lite",
        temperature=0.0,
    )

    extractions = []
    success_count = 0
    error_count = 0
    total_tokens = 0

    for i, row in abstracts_df.iterrows():
        logger.info(f"\n[{i+1}/{len(abstracts_df)}] Extracting: {row['study_id']}")

        result = gemini.extract_from_abstract(
            abstract=row["abstract"],
            study_id=row["study_id"],
            doi=row["doi"],
            year=row["year"],
            journal=row["journal"],
        )

        extraction_record = {
            "study_id": row["study_id"],
            "pmid": row["pmid"],
            "doi": row["doi"],
            "success": result.success,
            "model": result.model,
            "temperature": result.temperature,
            "timestamp": result.timestamp,
            "tokens_used": result.tokens_used,
        }

        if result.success:
            extraction_record["data"] = result.data
            success_count += 1
            if result.tokens_used:
                total_tokens += result.tokens_used
            logger.info(f"  ✓ Success (tokens: {result.tokens_used})")
        else:
            extraction_record["error"] = result.error
            error_count += 1
            logger.error(f"  ✗ Failed: {result.error}")

        extractions.append(extraction_record)

        # Rate limiting (Gemini has generous limits, but be cautious)
        time.sleep(0.5)

    # ========================================================================
    # STEP 5: Save results
    # ========================================================================
    logger.info("\nStep 5: Saving extraction results...")

    # Save as JSONL (one JSON object per line)
    extractions_file = Path(args.output) / "extractions_sample_30.jsonl"
    with open(extractions_file, "w") as f:
        for extraction in extractions:
            f.write(json.dumps(extraction) + "\n")

    logger.info(f"Saved {len(extractions)} extractions to {extractions_file}")

    # Save summary
    summary = {
        "test_metadata": {
            "date": datetime.utcnow().isoformat() + "Z",
            "model": "gemini-2.5-flash-lite",
            "temperature": 0.0,
            "total_samples": len(extractions),
            "target_limit": args.limit,
        },
        "results": {
            "success": success_count,
            "errors": error_count,
            "success_rate": success_count / len(extractions) if extractions else 0,
        },
        "token_usage": {
            "total_tokens": total_tokens,
            "avg_tokens_per_extraction": total_tokens / success_count
            if success_count > 0
            else 0,
        },
        "extraction_file": str(extractions_file),
        "abstracts_file": str(abstracts_file),
    }

    summary_file = Path(args.output) / "extraction_summary_30.json"
    save_json(summary, summary_file)

    # ========================================================================
    # STEP 6: Print summary
    # ========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTION TEST COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total samples: {len(extractions)}")
    logger.info(f"Successful: {success_count} ({success_count/len(extractions)*100:.1f}%)")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Total tokens used: {total_tokens:,}")
    logger.info(
        f"Avg tokens/extraction: {total_tokens/success_count if success_count > 0 else 0:.0f}"
    )
    logger.info(f"\nResults saved to: {args.output}")
    logger.info(f"  - Extractions: {extractions_file}")
    logger.info(f"  - Abstracts: {abstracts_file}")
    logger.info(f"  - Summary: {summary_file}")

    # Sample successful extraction
    if success_count > 0:
        logger.info("\n" + "=" * 60)
        logger.info("SAMPLE EXTRACTION (first successful):")
        logger.info("=" * 60)

        sample = next((e for e in extractions if e["success"]), None)
        if sample and "data" in sample:
            logger.info(f"\nStudy: {sample['study_id']}")
            logger.info(f"Outcome: {sample['data']['outcome_context']['measure_name']}")
            logger.info(f"Effect: {sample['data']['effect']['effect_point']} ({sample['data']['effect']['ci_low']}, {sample['data']['effect']['ci_high']})")
            logger.info(f"Population: {sample['data']['clinical_context']['population']}")
            logger.info(f"\nFull extraction saved in JSONL file")

    return 0


if __name__ == "__main__":
    sys.exit(main())
