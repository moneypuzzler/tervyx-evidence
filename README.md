# TERVYX-EVIDENCE (C Repo)

**Evidence Extraction Pipeline for TERVYX Protocol**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Purpose

**Role (Single Responsibility):**

- **Find** papers (search)
- **Match** papers to entries (relevance)
- **Extract** numbers from tables/text (LLM temperature=0, JSON mode)
- **Output** structured ESV (Evidence State Vector) as `evidence.csv`

**Critical Boundary: LLM as "EXTRACTOR", NOT "JUDGE"**

- ✅ **Allowed**: Exact numerical extraction from papers
- ❌ **Prohibited**: Effect size calculation, missing value imputation, "likely/probable" judgments, final labeling

**Final labeling/meta-analysis/gates happen in A repo (tervyx) via deterministic policy-as-code pipeline.**

---

## Repository Structure

```
tervyx-evidence/
├── config/                      # Configuration files
│   ├── entry_catalog.yaml       # 12 seed entries (health, balanced)
│   ├── extraction_policy.yaml   # LLM usage rules & boundaries
│   ├── phi_precheck.yaml        # Φ-gate pre-screening (physical impossibilities)
│   ├── k_precheck.yaml          # K-gate pre-screening (safety signals)
│   └── sources.yaml             # PubMed/Crossref API configs
├── protocol/
│   └── esv.schema.json          # ESV schema (A repo contract)
├── src/
│   ├── catalog/                 # Entry catalog loader
│   ├── gates_precheck/          # Φ/K early rejection filters
│   ├── search/                  # PubMed/Crossref clients
│   ├── matching/                # Paper-entry relevance matching
│   ├── extraction/              # LLM extraction (JSON mode, temp=0)
│   ├── export/                  # Export to A/D repos
│   └── common/                  # I/O, hashing, logging utilities
├── tools/
│   ├── generate_evidence.py    # Main pipeline (single entry)
│   ├── build_from_catalog.py   # Batch processing (all entries)
│   ├── export_pipeline_runner.py  # Export to A/D repos
│   └── quick_smoke_tests.py    # Structural validation tests
└── outputs/
    └── evidence_catalog/        # Generated ESV outputs
```

---

## Data Flow

### C → A → D → B Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ C (tervyx-evidence) - THIS REPO                             │
│   Search → Match → Extract → evidence.csv (ESV)             │
│   • LLM: temperature=0, JSON mode                           │
│   • NO judgment/calculation                                 │
└──────────────────┬──────────────────────────────────────────┘
                   │ evidence.csv
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ A (tervyx) - Deterministic Build Pipeline                   │
│   REML+MC → Gates (Φ/R/J/K/L) → TEL-5 → Artifacts          │
│   • policy.yaml: TEL-5 thresholds, δ, gates, fingerprint   │
│   • LLM-FREE (except C's extraction)                        │
└──────────────────┬──────────────────────────────────────────┘
                   │ entry.jsonld, simulation.json, citations.json
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ D (tervyx-entries) - Data Catalog / Encyclopedia            │
│   Permanent storage of evidence + artifacts                 │
└──────────────────┬──────────────────────────────────────────┘
                   │ Read-only
                   ↓
┌─────────────────────────────────────────────────────────────┐
│ B (tervyx-analysis) - LLM-Free Reporting                    │
│   pandas/numpy/matplotlib → Figures/Reports                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.10+
- NCBI account (for PubMed API)

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/tervyx-evidence.git
cd tervyx-evidence

# Install dependencies
pip install -e .

# Or install with dev tools
pip install -e ".[dev]"

# Set environment variables
cp .env.example .env
# Edit .env with your NCBI_API_KEY and TERVYX_EMAIL
```

### Environment Variables

Create `.env` file:

```bash
# Required
TERVYX_EMAIL=your.email@example.com

# Optional (increases PubMed rate limit from 3/sec to 10/sec)
NCBI_API_KEY=your_ncbi_api_key

# LLM APIs (if implementing real extraction)
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

### 1. Generate Evidence for Single Entry

```bash
python tools/generate_evidence.py \
  --entry-id SLP-MG-GLY-PSQI \
  --catalog config/entry_catalog.yaml \
  --output outputs/evidence_catalog
```

Output:
```
outputs/evidence_catalog/supplements/minerals/magnesium-glycinate/sleep/v1/
├── evidence.csv            # ESV (main output)
├── metadata.json           # Entry metadata
├── extraction_log.json     # Extraction provenance
└── manifest.json           # File hashes
```

### 2. Build All Entries from Catalog

```bash
python tools/build_from_catalog.py \
  --catalog config/entry_catalog.yaml \
  --output outputs/evidence_catalog \
  --max-per-entry 5
```

### 3. Export to A Repo (for deterministic build)

```bash
python tools/export_pipeline_runner.py \
  --mode to-a \
  --source outputs/evidence_catalog \
  --target ../tervyx/entries
```

### 4. Export to D Repo (data catalog)

```bash
python tools/export_pipeline_runner.py \
  --mode to-d \
  --source outputs/evidence_catalog \
  --target ../tervyx-entries
```

### 5. Run Smoke Tests

```bash
python tools/quick_smoke_tests.py
```

---

## Evidence State Vector (ESV) Schema

**Contract with A Repo:**

`evidence.csv` MUST contain these columns:

| Column | Type | Description |
|--------|------|-------------|
| `study_id` | string | Unique study ID (e.g., "Nguyen2022") |
| `year` | int | Publication year (1990-2025) |
| `design` | string | Study design (e.g., "randomized controlled trial") |
| `effect_type` | string | SMD, MD, OR, RR, HR |
| `effect_point` | float | Effect size point estimate (EXACT copy from paper) |
| `ci_low` | float | 95% CI lower bound (EXACT copy) |
| `ci_high` | float | 95% CI upper bound (EXACT copy) |
| `n_treat` | int | Treatment group sample size |
| `n_ctrl` | int | Control group sample size |
| `risk_of_bias` | string | low, moderate, high, unclear |
| `doi` | string | DOI (without https://doi.org/ prefix) |
| `journal_id` | string | Journal identifier for J-Oracle lookup |

**Critical Rules:**

- ❌ **NO calculation** of effect sizes (must be exact copy from paper)
- ❌ **NO imputation** of missing CI (leave blank if absent)
- ❌ **NO unit conversion** (A repo handles via category δ)
- ❌ **NO aggregation** of subgroups (one row = one study outcome)

Full schema: [`protocol/esv.schema.json`](protocol/esv.schema.json)

---

## Pipeline Stages

### 1. Φ-Gate Pre-check (Physical Plausibility)

Rejects obvious impossibilities **before** expensive search/extraction:

- Non-contact devices with systemic claims (e.g., magnetic bracelet → blood pressure)
- Topical applications without transdermal mechanism → systemic effects
- Prohibited substances (germanium, colloidal silver, aristolochic acid)

Config: [`config/phi_precheck.yaml`](config/phi_precheck.yaml)

### 2. K-Gate Pre-check (Safety Signals)

Flags safety concerns:

- High-risk substances (ephedra, kava, etc.)
- Dose-dependent toxicity thresholds
- Major drug-supplement interactions
- Regulatory warnings (FDA, EMA)

Config: [`config/k_precheck.yaml`](config/k_precheck.yaml)

### 3. Search (PubMed/Crossref)

- Default: PubMed with RCT filter
- Rate limits: 3 req/sec (10 with API key)
- Filters: humans, English, RCT

Config: [`config/sources.yaml`](config/sources.yaml)

### 4. Matching (Relevance Scoring)

Score papers against entry criteria:

- Intervention match: 30%
- Outcome match: 30%
- Design match (RCT): 20%
- Population match: 20%

Threshold: 0.7 (configurable)

### 5. Extraction (LLM, temperature=0)

**Status: PLACEHOLDER** (requires API keys)

Real implementation needs:
- OpenAI/Anthropic API client
- Structured prompts with JSON schema enforcement
- Table/figure parsing
- Retry logic & cost tracking

Current behavior: Generates **MOCK data** for demonstration.

### 6. Validation

- Schema conformance (ESV required fields)
- Type checking (numeric ranges, DOI format)
- Consistency checks (CI order, sample sizes > 0)

### 7. Output & Manifest

- `evidence.csv` (ESV)
- `metadata.json` (entry info, gate verdicts, timestamps)
- `extraction_log.json` (provenance: source locations, model info)
- `manifest.json` (file hashes for integrity)

---

## Seed Catalog (12 Entries)

**Domain-balanced initial set:**

| ID | Domain | Intervention | Outcome | Type |
|----|--------|--------------|---------|------|
| SLP-MG-GLY-PSQI | Sleep | Magnesium glycinate | PSQI | supplement |
| SLP-TEA-LAT | Sleep | Green tea | Latency | food |
| CARD-BEET-SBP | Cardio | Beetroot | SBP | food |
| CARD-AEREX-SBP | Cardio | Aerobic exercise | SBP | behavioral |
| CARD-GARLIC-LDL | Cardio | Garlic | LDL | food |
| MENT-ASHW-GAD7 | Mental | Ashwagandha | GAD-7 | supplement |
| MENT-MIND-DEP | Mental | Mindfulness | PHQ-9 | behavioral |
| COG-OM3-MOCA | Cognition | Omega-3 | MoCA | supplement |
| META-BERB-A1C | Metabolic | Berberine | HbA1c | supplement |
| DEV-REDLIGHT-SLEEP | Sleep | Red light therapy | Sleep | device |
| PROC-ACU-PAIN | Pain | Acupuncture | VAS | procedure |
| SAFE-KIDNEY-EGFR | Safety | (any) | eGFR | safety |

Full catalog: [`config/entry_catalog.yaml`](config/entry_catalog.yaml)

---

## LLM Usage Policy

**From [`config/extraction_policy.yaml`](config/extraction_policy.yaml):**

### ✅ Allowed Operations

- Locate table coordinates (e.g., "Table 2, Row 3")
- Copy exact numbers from text/tables
- Identify text snippets with numbers
- Parse structured formats (HTML tables, XML)

### ❌ Prohibited Operations

- Calculate effect sizes (e.g., raw mean → SMD)
- Estimate missing CI (e.g., SE → 95% CI)
- Infer sample sizes (e.g., "about 50" → n=50)
- Convert units (e.g., mg/dL → mmol/L)
- Aggregate subgroups (e.g., men + women)
- Extrapolate timepoints (e.g., 4-week → 8-week)

### Settings

- `temperature: 0` (mandatory for reproducibility)
- `response_format: json_object` (structured output enforcement)
- All prompts & responses logged for audit
- Cost tracking & retry logic with backoff

---

## Integration with A/D Repos

### A Repo (tervyx) - Deterministic Pipeline

**Handoff:**

C produces `evidence.csv` → A reads it → A computes:

1. Meta-analysis (REML + Monte Carlo)
2. Gates (Φ/R/J/K/L) from `policy.yaml`
3. TEL-5 classification (Gold/Silver/Bronze/Red/Black)
4. `policy_fingerprint` (sha256 of policy + snapshots)

**Artifacts A generates:**

- `entry.jsonld` (final label, tier, P(effect>δ), gates)
- `simulation.json` (MC draws, posterior)
- `citations.json` (formatted references)

**Path convention:**

A reads from: `entries/{intervention_type}/{subcategory}/{product}/{outcome}/v{version}/evidence.csv`

### D Repo (tervyx-entries) - Data Catalog

**Pure storage:**

- Receives ESV from C (or artifacts from A)
- No computation, just archival
- A & B read from D for analysis

---

## CI/CD

`.github/workflows/ci.yml` runs on push:

- ✅ Lint (black, ruff)
- ✅ Type check (mypy)
- ✅ Smoke tests (structure, schema, gates)
- ✅ ESV schema validation
- ✅ Manifest integrity checks

---

## Development Roadmap

### Phase 1: Foundation (✅ Complete)

- [x] Repository structure
- [x] Config files (catalog, policies, gates)
- [x] ESV schema definition
- [x] Module skeletons (catalog, search, matching, export)
- [x] CLI tools (generate, build, export)
- [x] Smoke tests

### Phase 2: Search & Matching (Next)

- [ ] PubMed integration testing with real API
- [ ] Crossref supplementary search
- [ ] Enhanced matching (keyword + semantic)
- [ ] PDF download & caching

### Phase 3: Extraction (Core)

- [ ] OpenAI/Anthropic API integration
- [ ] Structured prompt engineering
- [ ] Table parsing (HTML, PDF)
- [ ] JSON schema validation
- [ ] Retry logic & cost tracking
- [ ] Extract → Validate → ESV pipeline

### Phase 4: Integration

- [ ] A repo runner script (C → A → D flow)
- [ ] B repo analysis hooks (D → figures)
- [ ] Policy RFC workflow
- [ ] DAG partial re-evaluation

### Phase 5: Scale & Quality

- [ ] Parallel processing (multi-entry builds)
- [ ] Advanced PDF parsing (GROBID)
- [ ] Semi-automated quality checks
- [ ] Cost optimization (caching, model selection)

---

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

**Development setup:**

```bash
pip install -e ".[dev]"
black src/ tools/
ruff check src/ tools/
mypy src/
pytest tests/
```

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Citation

If you use TERVYX-EVIDENCE in research, please cite:

```bibtex
@software{tervyx_evidence_2025,
  title={TERVYX-EVIDENCE: Reproducible Evidence Extraction for Policy-as-Code Evaluation},
  author={TERVYX Team},
  year={2025},
  url={https://github.com/your-org/tervyx-evidence}
}
```

---

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/your-org/tervyx-evidence/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/tervyx-evidence/discussions)
- **Email**: contact@tervyx.org

---

## References

- **A Repo (tervyx)**: Deterministic build pipeline
- **D Repo (tervyx-entries)**: Data catalog
- **B Repo (tervyx-analysis)**: LLM-free reporting
- **Paper**: "TERVYX Protocol: A Reproducible Policy-as-Code Standard for Trustworthy Knowledge in the AI Era"

---

**Philosophy:** _"Authority is not the source of truth. Reproducibility is."_
