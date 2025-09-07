#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Pass limit argument if provided
LIMIT_ARG=""
if [ $# -gt 0 ]; then
    LIMIT_ARG="$1"
fi

# Run the content fetcher with error handling
python3 content_fetcher.py $LIMIT_ARG 2>&1 | tee -a logs/content_fetcher.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): Content fetcher failed with exit code $?" >> logs/content_fetcher_errors.log
    exit 1
fi

echo "$(date): Content fetcher completed successfully" >> logs/content_fetcher.log