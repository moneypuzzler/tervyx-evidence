# TERVYX Evidence Extraction Guide

**30-Sample Test with Gemini 2.5 Flash Lite**

---

## Quick Start (5 Minutes)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `google-generativeai>=0.3.0` - Gemini API client
- `biopython>=1.81` - PubMed/NCBI access
- `pandas`, `pyyaml`, `jsonschema` - Data handling

### 2. Set API Keys

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Required
TERVYX_EMAIL=your.email@example.com
GEMINI_API_KEY=your_google_api_key_here

# Optional (for faster PubMed access)
NCBI_API_KEY=your_ncbi_key_here
```

**Get API Keys:**
- **Gemini**: https://makersuite.google.com/app/apikey (FREE tier available)
- **NCBI**: https://www.ncbi.nlm.nih.gov/account/settings/ (optional, increases rate limit)

### 3. Run 30-Sample Extraction

```bash
export GEMINI_API_KEY=your_key
export TERVYX_EMAIL=your@email.com

python tools/run_30_sample_extraction.py --limit 30
```

**Expected runtime:** 3-5 minutes (depends on PubMed search + Gemini processing)

---

## What It Does

### Step 1: PubMed Search
- Searches for sleep-related RCTs from catalog
- Filters: randomized controlled trial, humans, English
- Collects ~30 abstracts with metadata

### Step 2: Save Abstracts
- Saves to `abstracts/sleep/abstracts_sample_30.csv`
- Columns: study_id, pmid, doi, year, journal, title, abstract, authors

### Step 3: Gemini Extraction (temp=0)
- Model: `gemini-2.5-flash-lite`
- Temperature: **0** (deterministic)
- Extracts structured JSON from each abstract:
  - **Outcome context**: measure name, type, units, direction
  - **Effect sizes**: point estimate, CI, p-value
  - **Clinical context**: population, intervention, duration
  - **Narrative**: author conclusions, key quotes
  - **Safety**: adverse events

### Step 4: Save Results
- `extractions/sleep/extractions_sample_30.jsonl` - Full extractions (JSONL)
- `extractions/sleep/extraction_summary_30.json` - Summary stats

---

## Output Files

### `abstracts/sleep/abstracts_sample_30.csv`
```csv
study_id,pmid,doi,year,journal,title,abstract,authors,pmc_id
Abbasi2012,37611507,10.1007/...,2012,J Res Med Sci,"Effect of magnesium...","BACKGROUND: ... RESULTS: ...",Abbasi B; Kimiagar M; ...,
```

### `extractions/sleep/extractions_sample_30.jsonl`
Each line = 1 extraction (JSON):
```json
{
  "study_id": "Abbasi2012",
  "success": true,
  "model": "gemini-2.5-flash-lite",
  "temperature": 0.0,
  "tokens_used": 2847,
  "data": {
    "outcome_context": {
      "measure_name": "ISI score",
      "measure_type": "validated_scale",
      "units": "points",
      "direction": "decrease_is_benefit"
    },
    "effect": {
      "effect_point": -7.2,
      "ci_low": -9.1,
      "ci_high": -5.3,
      "p_value": "<0.001"
    },
    "clinical_context": {
      "population": "elderly with insomnia",
      "intervention_description": "magnesium 500mg/day for 8 weeks"
    },
    "narrative": {
      "author_conclusion": "Magnesium appears effective for improving sleep in elderly"
    }
  }
}
```

### `extractions/sleep/extraction_summary_30.json`
```json
{
  "test_metadata": {
    "date": "2025-11-11T...",
    "model": "gemini-2.5-flash-lite",
    "temperature": 0.0
  },
  "results": {
    "success": 28,
    "errors": 2,
    "success_rate": 0.933
  },
  "token_usage": {
    "total_tokens": 73824,
    "avg_tokens_per_extraction": 2636
  }
}
```

---

## Cost Estimation

**Gemini 2.5 Flash Lite Pricing (as of Nov 2025):**
- Input: $0.075 / 1M tokens
- Output: $0.30 / 1M tokens

**30-sample test:**
- ~75K tokens total (~2,500 tokens/abstract)
- **Estimated cost: $0.02 - $0.05** (negligible)

**1,000 entries (full catalog):**
- ~2.5M tokens
- **Estimated cost: $0.50 - $2.00**

---

## Validation & Quality Checks

### Automatic Validation
- Required fields present (measure_name, effect_point, ci_low/high, sample_sizes)
- Numeric types correct
- CI order valid (ci_low < ci_high for positive effects)

### Quality Flags
Each extraction includes:
```json
"quality_flags": {
  "extraction_confidence": "high | medium | low",
  "needs_manual_review": false,
  "data_source": "abstract_only"
}
```

### Manual Review Triggers
- Numbers unclear in abstract
- Multiple outcomes reported (ambiguous)
- Complex interventions
- Extraction confidence = "low"

---

## Next Steps After 30-Sample Test

### 1. Review Results
```bash
# Check summary
cat extractions/sleep/extraction_summary_30.json

# Review sample extractions
head -5 extractions/sleep/extractions_sample_30.jsonl | python -m json.tool
```

### 2. Quality Assessment
- Success rate target: >90%
- Token efficiency: <3,000 tokens/abstract
- Manual review rate: <10%

### 3. If Results Good → Scale Up
```bash
# Process full catalog (12 entries × ~5 studies = 60 total)
python tools/build_from_catalog.py \
  --catalog config/entry_catalog.yaml \
  --max-per-entry 5
```

### 4. Export to A Repo
```bash
# Convert JSONL → ESV + ESV_context CSV
python tools/make_evidence_from_extractions.py \
  --in extractions/sleep \
  --esv-out evidence/sleep/evidence.csv \
  --ctx-out evidence/sleep/evidence_context.csv

# Sync to A repo
python tools/export_pipeline_runner.py \
  --mode to-a \
  --source evidence/ \
  --target ../tervyx/entries/
```

---

## Troubleshooting

### Error: "GEMINI_API_KEY not found"
```bash
export GEMINI_API_KEY=your_key_here
# or add to .env file
```

### Error: "No papers found"
- Check PubMed is accessible
- Try broader search queries in `config/entry_catalog.yaml`
- Increase `max_results` parameter

### Error: "JSON parse error"
- Gemini occasionally returns non-JSON (rare with temp=0)
- Retry logic (3 attempts) usually fixes
- Check `extraction_summary_30.json` for error rate

### Low Success Rate (<80%)
- Check abstracts quality (some may not have numerical results)
- Review extraction prompt in `src/extraction/gemini_client.py`
- Consider filtering abstracts (require certain keywords)

---

## Schema Reference

### ESV (Numeric Evidence)
Defined in: `protocol/esv.schema.json`

Required fields:
- `study_id`, `year`, `design`
- `effect_type`, `effect_point`, `ci_low`, `ci_high`
- `n_treat`, `n_ctrl`
- `doi`, `journal_id`

### ESV_context (Clinical/Narrative Context)
Defined in: `protocol/esv_context.schema.json`

Sections:
- `outcome_context` - measure details
- `effect_context` - additional effect info
- `clinical_context` - population/intervention
- `narrative` - author interpretation
- `safety` - adverse events

---

## Philosophy: LLM as "Extractor" NOT "Judge"

**Allowed:**
- ✅ Copy numbers from abstract
- ✅ Identify outcome measure names
- ✅ Extract author conclusions (as quotes)

**Prohibited:**
- ❌ Calculate effect sizes
- ❌ Convert units
- ❌ Impute missing values
- ❌ Judge clinical significance

**Final judgment happens in A repo (tervyx) via policy-as-code:**
- Harmonize outcomes to category standards
- Compute REML + Monte Carlo meta-analysis
- Apply gates (Φ/R/J/K/L)
- Assign TEL-5 tier (Gold/Silver/Bronze/Red/Black)

---

## Support

**Issues:** https://github.com/your-org/tervyx-evidence/issues

**Questions:** See main README.md

**Philosophy:** _"Reproducibility over authority. Extract, don't interpret."_
