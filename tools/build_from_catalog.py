#!/usr/bin/env python3
"""
Build evidence for all entries in catalog.

Usage:
    python tools/build_from_catalog.py \
        --catalog config/entry_catalog.yaml \
        --output outputs/evidence_catalog \
        --max-per-entry 5
"""

import sys
import argparse
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.catalog.catalog_loader import CatalogLoader
from src.common.logging import setup_logger

logger = setup_logger("build_from_catalog")


def main():
    parser = argparse.ArgumentParser(description="Build evidence for all catalog entries")
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
        "--max-per-entry",
        type=int,
        default=5,
        help="Max studies per entry",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first error",
    )
    parser.add_argument(
        "--entry-ids",
        nargs="*",
        help="Process only specific entry IDs (optional)",
    )

    args = parser.parse_args()

    # Load catalog
    logger.info(f"Loading catalog: {args.catalog}")
    catalog = CatalogLoader(args.catalog)

    entries_to_process = catalog.get_all_entries()

    # Filter if specific IDs requested
    if args.entry_ids:
        entries_to_process = [e for e in entries_to_process if e.id in args.entry_ids]
        logger.info(f"Processing {len(entries_to_process)} specified entries")
    else:
        logger.info(f"Processing all {len(entries_to_process)} entries")

    # Process each entry
    success_count = 0
    failure_count = 0

    for i, entry in enumerate(entries_to_process, 1):
        logger.info(f"\n[{i}/{len(entries_to_process)}] Processing: {entry.id}")

        # Call generate_evidence.py as subprocess
        cmd = [
            sys.executable,
            "tools/generate_evidence.py",
            "--entry-id",
            entry.id,
            "--catalog",
            args.catalog,
            "--output",
            args.output,
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=False)
            success_count += 1
            logger.info(f"✓ {entry.id} completed")

        except subprocess.CalledProcessError as e:
            failure_count += 1
            logger.error(f"✗ {entry.id} failed with code {e.returncode}")

            if args.fail_fast:
                logger.error("Fail-fast enabled, stopping")
                return 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("BUILD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total entries: {len(entries_to_process)}")
    logger.info(f"Success: {success_count}")
    logger.info(f"Failures: {failure_count}")
    logger.info(f"Output: {args.output}")

    if failure_count > 0:
        logger.warning(f"{failure_count} entries failed")
        return 1

    logger.info("✓ All entries processed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
