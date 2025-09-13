#!/bin/bash
#
# AI Analyzer Script - Analyzes extracted articles using BART models
#
# Usage Examples:
#   ./run_ai_analyzer.sh                    # Process all extracted files
#   ./run_ai_analyzer.sh 10                 # Process 10 files
#
# Parameters:
#   $1 (optional): Limit - Number of files to process (leave empty for all)
#
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Check for help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "AI Analyzer Script - Analyzes extracted article content using BART models"
    echo ""
    echo "Usage: ./run_ai_analyzer.sh [LIMIT]"
    echo ""
    echo "Parameters:"
    echo "  LIMIT              (optional): Number of files to process (leave empty for all)"
    echo ""
    echo "Examples:"
    echo "  ./run_ai_analyzer.sh                    # Process all extracted files"
    echo "  ./run_ai_analyzer.sh 10                 # Process 10 files"
    echo ""
    echo "Features:"
    echo "  - BART-based text summarization"
    echo "  - Domain classification (news, sports, politics, etc.)"
    echo "  - Content analysis and metadata generation"
    echo "  - Status tracking and resume capability"
    exit 0
fi

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Pass arguments if provided (limit)
ARGS=""
if [ $# -gt 0 ]; then
    ARGS="$*"
fi

# Run the AI analyzer with error handling
python3 ai_analyzer.py $ARGS 2>&1 | tee -a logs/ai_analyzer.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): AI analyzer failed with exit code $?" >> logs/ai_analyzer_errors.log
    exit 1
fi

echo "$(date): AI analyzer completed successfully" >> logs/ai_analyzer.log