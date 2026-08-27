# CLO Extraction Prototype - Setup & Running

## Prerequisites

You need:
- Python 3.9+
- Anthropic API key (from https://console.anthropic.com)
- pip (Python package manager)

## Installation

```bash
# 1. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
export ANTHROPIC_API_KEY="sk-ant-..." # Replace with your key
# On Windows PowerShell:
# $env:ANTHROPIC_API_KEY="sk-ant-..."
```

## Running the Extraction

```bash
python3 clo_extractor.py
```

This will:
1. Read `sample_clo_memo.txt`
2. Call Claude API to extract structured data
3. Save outputs:
   - `clo_extraction.json` - Raw extracted data
   - `clo_extraction.xlsx` - Multi-sheet Excel workbook

## What Gets Extracted

### Summary Sheet
- Fund name, trustee, portfolio manager
- Key metrics: Portfolio size, WAC, WAL, default rate
- Covenant compliance status

### Sectors Sheet
- Sector breakdown (Tech, Healthcare, etc.)

### Credit Quality Sheet
- Distribution by rating (AAA, AA, A, BBB, BB, B, CCC)

### Class Notes Sheet
- All class notes with coupon, balance, rating

### Covenants Sheet
- Covenant names and compliance status

### Credit Events Sheet
- Notable defaults, downgrades, watch list items

## Using with Real Memos

1. **Save your memo as text** (if PDF, OCR first or copy text)
2. **Modify line in clo_extractor.py:**
   ```python
   memo_file = "your_memo_file.txt"  # Change this
   ```
3. **Run**: `python3 clo_extractor.py`

## Extending the Extractor

To extract different fields:
1. Edit the `extraction_prompt` in `extract_data()` method
2. Add new JSON fields you want Claude to extract
3. Add matching Excel sheets in `save_excel()` method

## Next Steps for Production

- Add PDF reading (pdfplumber or PyPDF2)
- Build FastAPI endpoint for batch processing
- Add database storage (SQLite or PostgreSQL)
- Create Telegram bot for email-based memo submission
- Add caching to avoid re-extracting same memos
