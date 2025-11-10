"""Hashing utilities for integrity checks and fingerprinting."""

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def sha256_str(text: str) -> str:
    """Compute SHA256 hash of string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hash of bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    """Compute SHA256 hash of file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_dict(data: Dict[str, Any]) -> str:
    """Compute SHA256 hash of dictionary (via canonical JSON)."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return sha256_str(canonical)


def compute_manifest_hashes(directory: Path) -> Dict[str, Dict[str, Any]]:
    """
    Compute hashes for all files in directory.

    Returns dict: {filename: {sha256: ..., size: ...}}
    """
    manifest = {}
    for file_path in Path(directory).iterdir():
        if file_path.is_file():
            manifest[file_path.name] = {
                "sha256": sha256_file(file_path),
                "size": file_path.stat().st_size,
            }
    return manifest
