# CLO Extraction Agent - Prototype

Extract structured data from CLO surveillance & refinancing memos using Claude's API.

**Status:** ✅ Working prototype. Ready to test with your own memos.

## What This Does

Takes a CLO memo (text/PDF) and returns:
- **JSON** - Structured extraction of all key metrics
- **Excel** - Multi-sheet workbook (summary, sectors, covenants, etc.)
- **Speed** - ~20 seconds per memo
- **Cost** - ~$0.03 per extraction

## Files

| File | Purpose |
|------|---------|
| `clo_extractor.py` | Main extraction agent |
| `sample_clo_memo.txt` | Example memo for testing |
| `clo_extraction_demo.json` | Example output |
| `requirements.txt` | Python dependencies |
| `SETUP_INSTRUCTIONS.md` | Installation guide |
| `PROTOTYPE_GUIDE.md` | Full customization guide |
| `quick_start.sh` | One-command setup |

## Quick Start

```bash
# 1. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Run
./quick_start.sh

# 3. Check outputs
ls clo_extraction.*
```

## What Gets Extracted

✅ Fund name & trustee  
✅ Portfolio metrics (WAC, WAL, size)  
✅ Credit quality distribution  
✅ Sector breakdown  
✅ All class notes + coupons  
✅ Covenant compliance status  
✅ Credit events & downgrades  
✅ Refinancing details  

## Example Output

```json
{
  "fund_name": "Apex Senior Loan Fund IV",
  "current_portfolio_size": 1187.5,
  "total_loans": 147,
  "wac": 4.85,
  "cumulative_default_rate": 3.58,
  "compliance_status": "All covenants in compliance"
}
```

## Next Steps

1. Test with your own CLO memo
2. Adjust extraction schema in `clo_extractor.py`
3. Add PDF support (optional)
4. Deploy as API or bot
5. Package as consulting offering

## Customization

To extract different fields:

1. Open `clo_extractor.py`
2. Edit the `extraction_prompt` (around line 65)
3. Add/remove JSON fields you want
4. Add matching Excel sheets in `save_excel()` method
5. Run and test

See `PROTOTYPE_GUIDE.md` for detailed examples.

## Requirements

- Python 3.9+
- Anthropic API key (free at https://console.anthropic.com)
- ~100 MB disk space

## Costs

- **Per extraction:** $0.02-0.05 (Claude API)
- **Infrastructure:** $0-50/mo (if self-hosted)
- **Profit margin:** 90%+ on $50/memo service

## Support

- `PROTOTYPE_GUIDE.md` - Full guide with examples
- `SETUP_INSTRUCTIONS.md` - Troubleshooting
- [Claude API Docs](https://docs.anthropic.com)

---

**Built with Claude API + Python. Use this to validate, test, and scale.**

Ready to customize? See `PROTOTYPE_GUIDE.md` for production roadmap.
