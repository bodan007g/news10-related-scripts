#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the text extractor with error handling
python3 text_extractor.py 2>&1 | tee -a logs/text_extractor.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): Text extractor failed with exit code $?" >> logs/text_extractor_errors.log
    exit 1
fi

echo "$(date): Text extractor completed successfully" >> logs/text_extractor.log