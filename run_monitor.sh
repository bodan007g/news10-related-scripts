#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

# Activate virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

# Change to script directory
cd "$SCRIPT_DIR"

# Run the monitoring script
python3 monitor_pipeline.py 2>&1 | tee -a logs/monitor.log

echo "$(date): Monitoring completed" >> logs/monitor.log