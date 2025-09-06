#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the content fetcher with error handling
python3 content_fetcher.py 2>&1 | tee -a logs/content_fetcher.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): Content fetcher failed with exit code $?" >> logs/content_fetcher_errors.log
    exit 1
fi

echo "$(date): Content fetcher completed successfully" >> logs/content_fetcher.log