"""I/O utilities for reading/writing configs, CSVs, JSON."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


def load_yaml(path: Path | str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], path: Path | str) -> None:
    """Save data as YAML."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(path: Path | str) -> Dict[str, Any] | List[Any]:
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any] | List[Any], path: Path | str, indent: int = 2) -> None:
    """Save data as JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_evidence_csv(path: Path | str) -> pd.DataFrame:
    """Load evidence.csv with strict schema validation."""
    df = pd.read_csv(path)

    # Validate required columns
    required_cols = [
        "study_id", "year", "design", "effect_type", "effect_point",
        "ci_low", "ci_high", "n_treat", "n_ctrl", "risk_of_bias", "doi", "journal_id"
    ]

    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return df


def save_evidence_csv(df: pd.DataFrame, path: Path | str) -> None:
    """Save DataFrame as evidence.csv."""
    df.to_csv(path, index=False, encoding="utf-8")


def ensure_dir(path: Path | str) -> Path:
    """Ensure directory exists, create if not."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: Path | str) -> str:
    """Read text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(text: str, path: Path | str) -> None:
    """Write text to file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
