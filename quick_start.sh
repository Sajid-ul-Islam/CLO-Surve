ok#!/bin/bash
# Quick start script for CLO Extraction prototype

echo "🚀 CLO Extraction - Quick Start"
echo "================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python 3.9+ first."
    exit 1
fi
echo "✅ Python 3 found"

# Check API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "⚠️  ANTHROPIC_API_KEY not set!"
    echo ""
    echo "To set it:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo ""
    echo "Get your key at: https://console.anthropic.com/account/keys"
    exit 1
fi
echo "✅ API key found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install --quiet -r requirements.txt 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "⚠️  Install failed. Try: pip install -r requirements.txt"
fi

# Run extraction
echo ""
echo "🔍 Running extraction on sample memo..."
echo ""
python3 clo_extractor.py

if [ -f "clo_extraction.json" ] && [ -f "clo_extraction.xlsx" ]; then
    echo ""
    echo "✅ Success! Files created:"
    echo "   - clo_extraction.json (structured data)"
    echo "   - clo_extraction.xlsx (Excel workbook)"
    echo ""
    echo "📖 Next: Read PROTOTYPE_GUIDE.md for customization"
else
    echo ""
    echo "❌ Something went wrong. Check error above."
    exit 1
fi
