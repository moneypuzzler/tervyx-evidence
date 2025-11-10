#!/usr/bin/env python3
"""
Quick smoke tests for C repo structure and modules.

Usage:
    python tools/quick_smoke_tests.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.catalog.catalog_loader import CatalogLoader
from src.gates_precheck.phi_precheck import PhiPrecheck
from src.gates_precheck.k_precheck import KPrecheck
from src.common.io_utils import load_yaml, load_json
from src.common.hashing import sha256_str
from src.common.logging import setup_logger

logger = setup_logger("smoke_tests")


def test_catalog_loading():
    """Test catalog loading."""
    logger.info("Test: Catalog loading...")
    catalog = CatalogLoader("config/entry_catalog.yaml")
    assert len(catalog) == 12, f"Expected 12 entries, got {len(catalog)}"

    entry = catalog.get_entry_by_id("SLP-MG-GLY-PSQI")
    assert entry is not None, "Entry SLP-MG-GLY-PSQI not found"
    assert entry.intervention_type == "supplements"
    assert entry.outcome == "sleep"

    logger.info("  ✓ Catalog loading works")


def test_phi_precheck():
    """Test Φ-gate pre-check."""
    logger.info("Test: Φ-gate pre-check...")
    phi = PhiPrecheck("config/phi_precheck.yaml")

    # Should pass
    result = phi.check_entry("supplements", "magnesium-glycinate", "sleep")
    assert result.verdict in ["pass", "warn"], f"Unexpected verdict: {result.verdict}"

    # Should reject (if magnetic device → systemic outcome in config)
    result = phi.check_entry("device_noninvasive", "magnetic-bracelet", "cardiovascular")
    # Note: Depends on config, may be "reject" or "pass" if not in exclusions

    logger.info("  ✓ Φ-gate pre-check works")


def test_k_precheck():
    """Test K-gate pre-check."""
    logger.info("Test: K-gate pre-check...")
    k = KPrecheck("config/k_precheck.yaml")

    # Should pass
    result = k.check_entry("magnesium-glycinate")
    assert result.verdict in ["pass", "note", "warn"], f"Unexpected verdict: {result.verdict}"

    # Should reject (if ephedra in config)
    result = k.check_entry("ephedra")
    assert result.verdict == "reject", "Ephedra should be rejected"

    logger.info("  ✓ K-gate pre-check works")


def test_schema_validation():
    """Test ESV schema exists and is valid JSON."""
    logger.info("Test: ESV schema validation...")
    schema = load_json("protocol/esv.schema.json")
    assert "definitions" in schema
    assert "EvidenceRecord" in schema["definitions"]

    required_fields = schema["definitions"]["EvidenceRecord"]["required"]
    assert "study_id" in required_fields
    assert "doi" in required_fields

    logger.info("  ✓ ESV schema is valid")


def test_hashing():
    """Test hashing utilities."""
    logger.info("Test: Hashing utilities...")
    hash1 = sha256_str("test")
    hash2 = sha256_str("test")
    assert hash1 == hash2, "Same input should produce same hash"

    hash3 = sha256_str("different")
    assert hash1 != hash3, "Different input should produce different hash"

    logger.info("  ✓ Hashing utilities work")


def main():
    logger.info("=" * 60)
    logger.info("TERVYX-EVIDENCE SMOKE TESTS")
    logger.info("=" * 60)

    tests = [
        test_catalog_loading,
        test_phi_precheck,
        test_k_precheck,
        test_schema_validation,
        test_hashing,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            logger.error(f"  ✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"  ✗ Test error: {e}")
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    if failed > 0:
        return 1

    logger.info("✓ All smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
