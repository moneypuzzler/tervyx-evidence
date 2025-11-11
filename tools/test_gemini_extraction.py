#!/usr/bin/env python3
"""
Test Gemini extraction with sample abstracts (no PubMed needed).
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.extraction.gemini_client import GeminiExtractor
from src.common.logging import setup_logger
from src.common.io_utils import save_json, ensure_dir
import pandas as pd

logger = setup_logger("gemini_test", level="INFO")

# Sample abstracts from real sleep/magnesium RCTs
SAMPLE_ABSTRACTS = [
    {
        "study_id": "Abbasi2012",
        "pmid": "23853635",
        "doi": "10.7861/clinmedicine.12-3-235",
        "year": 2012,
        "journal": "Journal of Research in Medical Sciences",
        "title": "The effect of magnesium supplementation on primary insomnia in elderly",
        "abstract": """BACKGROUND: Insomnia is a common complaint in elderly. Magnesium is a naturally occurring mineral that is important for many systems in the body especially the muscles and nerves. This study was conducted to determine the effect of magnesium supplementation on primary insomnia in elderly. METHODS: This randomized double-blind placebo-controlled clinical trial was conducted on 46 elderly subjects. Subjects were randomly assigned to receive either 500 mg magnesium or placebo daily for 8 weeks. Insomnia severity index (ISI), sleep diary, sleep efficiency, sleep time, sleep latency, early morning awakening, serum magnesium, serum melatonin, serum renin and serum cortisol were measured. RESULTS: Magnesium supplementation resulted in statistically significant improvement in ISI score (mean difference -7.2, 95% CI -9.1 to -5.3, P < 0.001), sleep efficiency (mean difference 5.6%, 95% CI 3.1 to 8.1, P < 0.001), sleep time (mean difference 25.3 minutes, 95% CI 15.2 to 35.4, P < 0.001), and sleep latency (mean difference -17.4 minutes, 95% CI -24.2 to -10.6, P < 0.001) compared with the placebo group. Serum renin concentration increased significantly following magnesium supplementation (P = 0.03), but serum melatonin and cortisol did not show any significant changes. CONCLUSIONS: Magnesium supplementation appears effective for improving sleep in elderly with insomnia."""
    },
    {
        "study_id": "Rondanelli2011",
        "pmid": "21199787",
        "doi": "10.1007/s00394-010-0142-7",
        "year": 2011,
        "journal": "European Journal of Nutrition",
        "title": "The effect of melatonin, magnesium, and zinc supplementation on primary insomnia in long-term care facility residents in Italy",
        "abstract": """PURPOSE: To evaluate the effect of a dietary supplement containing melatonin (5 mg), magnesium (225 mg) as magnesium oxide, and zinc (11.25 mg) as zinc gluconate on primary insomnia in long-term care facility residents. METHODS: This was a randomized, double-blind, placebo-controlled clinical trial. 43 subjects with primary insomnia were randomly assigned to receive the active treatment or placebo nightly 1 h before bedtime for 8 weeks. Sleep quality was evaluated using the Pittsburgh Sleep Quality Index (PSQI). RESULTS: Compared with baseline, supplementation resulted in significant improvements in PSQI score (mean decrease -3.5 points, 95% CI -4.8 to -2.2, P < 0.001) versus placebo (mean decrease -0.3, 95% CI -1.1 to 0.5, P = 0.45). The between-group difference was statistically significant (P < 0.001). No serious adverse events were reported. CONCLUSIONS: The combination supplement containing melatonin, magnesium, and zinc appears to be a safe and effective treatment for primary insomnia in elderly institutionalized subjects."""
    },
    {
        "study_id": "Nielsen2010",
        "pmid": "20515551",
        "doi": "10.1016/j.sleep.2010.03.011",
        "year": 2010,
        "journal": "Sleep Medicine",
        "title": "Effects of magnesium supplementation on sleep quality in healthy adults",
        "abstract": """OBJECTIVE: To investigate whether oral magnesium supplementation improves sleep quality in healthy adults with mild sleep complaints. METHODS: A randomized, double-blind, placebo-controlled trial was conducted in 100 adults aged 18-65 years with subjective sleep complaints (PSQI > 5). Participants received either 300 mg elemental magnesium or placebo daily for 12 weeks. Primary outcome was change in PSQI total score. Secondary outcomes included sleep diary measures and serum magnesium levels. RESULTS: At 12 weeks, the magnesium group showed significant improvement in PSQI total score compared to placebo (mean difference -2.8, 95% CI -4.1 to -1.5, P < 0.001). Sleep efficiency improved by 7.2% in the magnesium group versus 1.3% in placebo (P = 0.002). Sleep onset latency decreased by 14.5 minutes in the magnesium group (P = 0.01). Total sleep time increased by 22 minutes (P = 0.03). Serum magnesium levels increased significantly in the treatment group (P < 0.001). No serious adverse events occurred; mild gastrointestinal symptoms were reported in 8% of magnesium group versus 3% of placebo. CONCLUSIONS: Oral magnesium supplementation significantly improves subjective sleep quality in adults with mild sleep complaints."""
    },
]

def main():
    logger.info("=" * 60)
    logger.info("GEMINI 2.5 FLASH LITE - EXTRACTION TEST")
    logger.info("Testing with 3 sample abstracts (no PubMed)")
    logger.info("=" * 60)

    # Initialize Gemini
    import os
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set!")
        return 1

    logger.info(f"✓ Gemini API key loaded")
    logger.info(f"Model: gemini-2.5-flash-lite")
    logger.info(f"Temperature: 0")

    gemini = GeminiExtractor(
        api_key=api_key,
        model="gemini-2.5-flash-lite",
        temperature=0.0,
    )

    # Create output directory
    output_dir = Path("extractions/sleep")
    ensure_dir(output_dir)

    # Extract each abstract
    extractions = []
    success_count = 0
    total_tokens = 0

    for i, sample in enumerate(SAMPLE_ABSTRACTS, 1):
        logger.info(f"\n[{i}/{len(SAMPLE_ABSTRACTS)}] Extracting: {sample['study_id']}")
        logger.info(f"  DOI: {sample['doi']}")

        result = gemini.extract_from_abstract(
            abstract=sample["abstract"],
            study_id=sample["study_id"],
            doi=sample["doi"],
            year=sample["year"],
            journal=sample["journal"],
        )

        extraction_record = {
            "study_id": sample["study_id"],
            "pmid": sample["pmid"],
            "doi": sample["doi"],
            "title": sample["title"],
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
            logger.error(f"  ✗ Failed: {result.error}")

        extractions.append(extraction_record)

    # Save results
    logger.info("\n" + "=" * 60)
    logger.info("SAVING RESULTS")
    logger.info("=" * 60)

    # Save JSONL
    jsonl_file = output_dir / "test_extractions.jsonl"
    with open(jsonl_file, "w") as f:
        for extraction in extractions:
            f.write(json.dumps(extraction) + "\n")
    logger.info(f"✓ Saved JSONL: {jsonl_file}")

    # Save summary
    summary = {
        "test_metadata": {
            "date": datetime.utcnow().isoformat() + "Z",
            "model": "gemini-2.5-flash-lite",
            "temperature": 0.0,
            "total_samples": len(extractions),
            "note": "Sample abstracts test (no PubMed search)",
        },
        "results": {
            "success": success_count,
            "errors": len(extractions) - success_count,
            "success_rate": success_count / len(extractions),
        },
        "token_usage": {
            "total_tokens": total_tokens,
            "avg_tokens_per_extraction": total_tokens / success_count if success_count > 0 else 0,
        },
    }

    summary_file = output_dir / "test_summary.json"
    save_json(summary, summary_file)
    logger.info(f"✓ Saved summary: {summary_file}")

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Success: {success_count}/{len(extractions)} ({success_count/len(extractions)*100:.1f}%)")
    logger.info(f"Total tokens: {total_tokens:,}")
    logger.info(f"Avg tokens/extraction: {total_tokens/success_count if success_count > 0 else 0:.0f}")

    # Show sample extraction
    if success_count > 0:
        logger.info("\n" + "=" * 60)
        logger.info("SAMPLE EXTRACTION")
        logger.info("=" * 60)

        sample = next((e for e in extractions if e["success"]), None)
        if sample and "data" in sample:
            data = sample["data"]
            logger.info(f"\nStudy: {sample['study_id']}")
            logger.info(f"Title: {sample['title'][:80]}...")

            if "outcome_context" in data:
                logger.info(f"\n✓ Outcome Context:")
                logger.info(f"  Measure: {data['outcome_context'].get('measure_name')}")
                logger.info(f"  Type: {data['outcome_context'].get('measure_type')}")
                logger.info(f"  Direction: {data['outcome_context'].get('direction')}")

            if "effect" in data:
                logger.info(f"\n✓ Effect:")
                logger.info(f"  Point: {data['effect'].get('effect_point')}")
                logger.info(f"  95% CI: ({data['effect'].get('ci_low')}, {data['effect'].get('ci_high')})")
                logger.info(f"  P-value: {data['effect'].get('p_value')}")

            if "clinical_context" in data:
                logger.info(f"\n✓ Clinical Context:")
                logger.info(f"  Population: {data['clinical_context'].get('population')}")
                logger.info(f"  Intervention: {data['clinical_context'].get('intervention_description')}")
                logger.info(f"  Duration: {data['clinical_context'].get('intervention_duration')}")

            if "narrative" in data:
                logger.info(f"\n✓ Narrative:")
                logger.info(f"  Conclusion: {data['narrative'].get('author_conclusion')[:100]}...")

            logger.info(f"\n✓ Full data saved in: {jsonl_file}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
