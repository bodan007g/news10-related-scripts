#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the AI analyzer with error handling
python3 ai_analyzer.py 2>&1 | tee -a logs/ai_analyzer.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): AI analyzer failed with exit code $?" >> logs/ai_analyzer_errors.log
    exit 1
fi

echo "$(date): AI analyzer completed successfully" >> logs/ai_analyzer.log