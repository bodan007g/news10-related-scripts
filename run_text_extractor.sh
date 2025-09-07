#!/bin/bash
#
# Text Extractor Script - Extracts clean article text from HTML files
#
# Usage Examples:
#   ./run_text_extractor.sh                                    # Process all files with newspaper (default)
#   ./run_text_extractor.sh 10                                 # Process 10 files with newspaper
#   ./run_text_extractor.sh 5 trafilatura                      # Process 5 files with trafilatura
#   ./run_text_extractor.sh 10 newspaper --save-cleaned-html   # Process 10 files and save cleaned HTML
#   ./run_text_extractor.sh "" trafilatura --save-cleaned-html # Process all files with trafilatura and save cleaned HTML
#
# Parameters:
#   $1 (optional): Limit - Number of HTML files to process (leave empty for all)
#   $2 (optional): Method - 'newspaper' (default, news-focused) or 'trafilatura' (faster, better metadata)
#   $3 (optional): --save-cleaned-html - Save cleaned HTML files alongside original files
#
# Methods Comparison:
#   trafilatura: Fast (~0.1s), excellent metadata extraction, AI-powered content detection
#   newspaper:   Slower (~0.3s), news-specific, good article detection, limited metadata
#
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Check for help flag
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Text Extractor Script - Extracts clean article text from HTML files"
    echo ""
    echo "Usage: ./run_text_extractor.sh [LIMIT] [METHOD] [--save-cleaned-html]"
    echo ""
    echo "Parameters:"
    echo "  LIMIT              (optional): Number of HTML files to process (leave empty for all)"
    echo "  METHOD             (optional): 'newspaper' (default) or 'trafilatura'"
    echo "  --save-cleaned-html (optional): Save cleaned HTML files alongside original files"
    echo ""
    echo "Examples:"
    echo "  ./run_text_extractor.sh                                    # Process all files with newspaper"
    echo "  ./run_text_extractor.sh 10                                 # Process 10 files with newspaper" 
    echo "  ./run_text_extractor.sh 5 trafilatura                      # Process 5 files with trafilatura"
    echo "  ./run_text_extractor.sh 10 newspaper --save-cleaned-html   # Process 10 files and save cleaned HTML"
    echo "  ./run_text_extractor.sh \"\" trafilatura --save-cleaned-html # Process all files with trafilatura and save cleaned HTML"
    echo ""
    echo "Methods Comparison:"
    echo "  newspaper:   Slower (~0.3s), news-focused, good article detection, limited metadata (DEFAULT)"
    echo "  trafilatura: Fast (~0.1s), excellent metadata, AI-powered, includes header formatting"
    echo ""
    echo "Features:"
    echo "  - Automatic header detection and Markdown formatting"
    echo "  - Smart Romanian language patterns"
    echo "  - Clean article text extraction"
    echo "  - Metadata extraction (title, author, date)"
    echo "  - Status tracking and resume capability"
    echo "  - Optional cleaned HTML saving (removes ads, scripts, navigation, etc.)"
    exit 0
fi

# Pass arguments if provided (limit and/or extraction method)
ARGS=""
if [ $# -gt 0 ]; then
    ARGS="$*"
fi

# Run the text extractor with error handling
python3 text_extractor.py $ARGS 2>&1 | tee -a logs/text_extractor.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): Text extractor failed with exit code $?" >> logs/text_extractor_errors.log
    exit 1
fi

echo "$(date): Text extractor completed successfully" >> logs/text_extractor.log