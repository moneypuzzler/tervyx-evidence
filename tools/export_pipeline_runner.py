#!/usr/bin/env python3
"""
Export evidence to A repo (tervyx) or D repo (tervyx-entries).

Usage:
    # Export to A repo (for deterministic build)
    python tools/export_pipeline_runner.py \
        --mode to-a \
        --source outputs/evidence_catalog \
        --target ../tervyx/entries

    # Export to D repo (data catalog)
    python tools/export_pipeline_runner.py \
        --mode to-d \
        --source outputs/evidence_catalog \
        --target ../tervyx-entries
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.export.export_to_a import ExportToA
from src.export.export_to_d import ExportToD
from src.common.logging import setup_logger

logger = setup_logger("export_pipeline")


def main():
    parser = argparse.ArgumentParser(description="Export evidence to A or D repo")
    parser.add_argument(
        "--mode",
        choices=["to-a", "to-d"],
        required=True,
        help="Export mode: to-a (A repo) or to-d (D repo)",
    )
    parser.add_argument(
        "--source",
        default="outputs/evidence_catalog",
        help="Source directory (C repo output)",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target directory (A repo entries/ or D repo root)",
    )
    parser.add_argument(
        "--copy-mode",
        choices=["sync", "evidence_only"],
        default="sync",
        help="Copy mode for to-a: sync (all files) or evidence_only",
    )

    args = parser.parse_args()

    source = Path(args.source)
    target = Path(args.target)

    if not source.exists():
        logger.error(f"Source directory does not exist: {source}")
        return 1

    if not target.exists():
        logger.warning(f"Target directory does not exist: {target}")
        logger.info("Creating target directory...")
        target.mkdir(parents=True, exist_ok=True)

    # Execute export
    if args.mode == "to-a":
        logger.info(f"Exporting to A repo: {target}")
        exporter = ExportToA(source, target)
        count = exporter.export_all(copy_mode=args.copy_mode)
        logger.info(f"✓ Exported {count} entries to A repo")

    elif args.mode == "to-d":
        logger.info(f"Mirroring to D repo: {target}")
        exporter = ExportToD(source, target)
        count = exporter.export_all()
        logger.info(f"✓ Mirrored {count} entries to D repo")

    return 0


if __name__ == "__main__":
    sys.exit(main())
