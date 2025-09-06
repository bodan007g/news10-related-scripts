#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the archive manager with error handling
python3 archive_manager.py 2>&1 | tee -a logs/archive_manager.log

# Check exit status
if [ $? -ne 0 ]; then
    echo "$(date): Archive manager failed with exit code $?" >> logs/archive_manager_errors.log
    exit 1
fi

echo "$(date): Archive manager completed successfully" >> logs/archive_manager.log