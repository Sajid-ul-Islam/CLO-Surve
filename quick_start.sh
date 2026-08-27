#!/bin/bash
# Quick start script for CLO Extraction prototype
# sudo-free + venv-aware (uses a local .venv managed by uv/pip)

set -e

echo "🚀 CLO Extraction - Quick Start"
echo "================================"
echo ""

# Resolve script directory so it works from anywhere
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

# Set up / reuse a local virtual environment (.venv)
if [ ! -d ".venv" ]; then
    echo ""
    echo "📦 Creating virtual environment (.venv)..."
    if command -v uv &> /dev/null; then
        uv venv .venv
    else
        python3 -m venv .venv
    fi
fi
# Activate (works for both bash and zsh-style activators)
# shellcheck disable=SC1091
source .venv/bin/activate
echo "✅ Using virtual environment: $(pwd)/.venv ($(python3 --version 2>&1))"

# Install dependencies (into the venv, no sudo needed)
echo ""
echo "📦 Installing dependencies..."
if command -v uv &> /dev/null; then
    uv pip install --quiet -r requirements.txt 2>/dev/null
else
    python3 -m pip install --quiet -r requirements.txt 2>/dev/null
fi
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "⚠️  Install failed. Try manually: source .venv/bin/activate && pip install -r requirements.txt"
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
