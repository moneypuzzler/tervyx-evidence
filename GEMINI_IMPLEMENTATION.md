# Gemini 2.5 Flash Lite Implementation

**Status:** ✅ Ready for 30-sample test (requires API keys)

---

## What's Implemented

### 1. Extended Schema (`protocol/esv_context.schema.json`)
Beyond numeric ESV (effect sizes), now captures:
- **Outcome context**: measure name, type, units, direction, assessment method
- **Effect context**: baseline, absolute/percent change, MCID, responder analysis
- **Clinical context**: population, intervention details, duration, setting
- **Narrative**: abstract full text, author conclusions, key quotes, spans
- **Safety**: adverse events mentions
- **Quality flags**: extraction confidence, manual review triggers

### 2. Gemini Client (`src/extraction/gemini_client.py`)
- Model: `gemini-2.5-flash-lite`
- Temperature: **0** (mandatory for reproducibility)
- JSON mode enforced
- Retry logic (3 attempts, exponential backoff)
- Token usage tracking
- Audit logging (model, temp, timestamp)

**Key Methods:**
- `extract_from_abstract()` - Main extraction
- `_build_extraction_prompt()` - Structured prompt
- `_validate_extraction()` - Field validation

### 3. 30-Sample Runner (`tools/run_30_sample_extraction.py`)
**Workflow:**
1. Load catalog (focus on sleep entries)
2. Search PubMed (RCTs, humans, English)
3. Save abstracts → `abstracts/sleep/abstracts_sample_30.csv`
4. Extract with Gemini → `extractions/sleep/extractions_sample_30.jsonl`
5. Generate summary → `extractions/sleep/extraction_summary_30.json`

**Output:**
- JSONL: One JSON object per line (easy to stream/parse)
- Summary: Success rate, token usage, error analysis

### 4. Directory Structure
```
abstracts/
  sleep/, cognition/, metabolic/, ... (8 categories)
extractions/
  sleep/, cognition/, metabolic/, ...
evidence/
  sleep/, cognition/, metabolic/, ...
```

### 5. Documentation
- `EXTRACTION_GUIDE.md` - Complete usage guide
- `.env.example` - API key setup
- `requirements.txt` - Gemini dependencies

---

## Usage

```bash
# 1. Install
pip install -r requirements.txt

# 2. Set API keys
export GEMINI_API_KEY=your_key
export TERVYX_EMAIL=your@email.com

# 3. Run 30-sample test
python tools/run_30_sample_extraction.py --limit 30

# 4. Review results
cat extractions/sleep/extraction_summary_30.json
head -3 extractions/sleep/extractions_sample_30.jsonl | python -m json.tool
```

---

## Cost Estimate

**Gemini 2.5 Flash Lite:**
- Input: $0.075 / 1M tokens
- Output: $0.30 / 1M tokens

**30 samples:** ~75K tokens = **$0.02-$0.05**
**1,000 entries:** ~2.5M tokens = **$0.50-$2.00**

---

## Next Steps (Requires API Key)

1. **Run 30-sample test**
   ```bash
   python tools/run_30_sample_extraction.py --limit 30
   ```

2. **Review quality**
   - Target success rate: >90%
   - Token efficiency: <3,000/abstract
   - Manual review rate: <10%

3. **If good → Scale up**
   ```bash
   # Full catalog (60 studies)
   python tools/build_from_catalog.py --max-per-entry 5
   ```

4. **Convert to ESV/ESV_context CSV**
   ```bash
   python tools/make_evidence_from_extractions.py \
     --in extractions/sleep \
     --esv-out evidence/sleep/evidence.csv \
     --ctx-out evidence/sleep/evidence_context.csv
   ```

5. **Export to A repo**
   ```bash
   python tools/export_pipeline_runner.py \
     --mode to-a \
     --target ../tervyx/entries/
   ```

---

## Critical Design Principles

### ✅ LLM as "Extractor" NOT "Judge"
- **Allowed**: Copy numbers, identify measures, extract quotes
- **Prohibited**: Calculate, convert, impute, judge significance

### ✅ Temperature = 0 (Reproducibility)
- Same abstract + same prompt = same output
- Verified by extraction_metadata in each record

### ✅ Audit Trail
Every extraction logs:
- Model name & version
- Temperature setting
- Timestamp
- Token usage
- Character spans (where numbers came from)

### ✅ Schema Separation
- **ESV** (numeric): A repo contract (unchanged)
- **ESV_context** (clinical/narrative): New, complements ESV
- Clean separation for future extensibility

---

## Files Changed/Added

**New:**
- `protocol/esv_context.schema.json` - Extended context schema
- `src/extraction/gemini_client.py` - Gemini client
- `tools/run_30_sample_extraction.py` - 30-sample runner
- `EXTRACTION_GUIDE.md` - User guide
- `GEMINI_IMPLEMENTATION.md` - This file

**Modified:**
- `requirements.txt` - Added google-generativeai
- `.env.example` - Added GEMINI_API_KEY

**Directories:**
- `abstracts/` - Raw abstract storage (8 categories)
- `extractions/` - JSONL extraction results
- `evidence/` - Final ESV + context CSV

---

## Ready to Test

All code is complete and ready for testing with real API keys.

**Waiting on:**
- GEMINI_API_KEY (get at: https://makersuite.google.com/app/apikey)
- TERVYX_EMAIL (any valid email for PubMed)
- (Optional) NCBI_API_KEY (for faster PubMed access)

**No code changes needed - just set environment variables and run!**
