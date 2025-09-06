#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the RSS generator with error handling
python3 rss_generator.py 2>&1 | tee -a logs/rss_generator.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): RSS generator failed with exit code $?" >> logs/rss_generator_errors.log
    exit 1
fi

echo "$(date): RSS generator completed successfully" >> logs/rss_generator.log