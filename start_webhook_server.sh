#!/bin/bash
# Start the multi-project webhook server in production mode
export SERVER_ENV=production
VHOSTS_BASE="/var/www/vhosts"

# Check if port 5000 is already in use
if lsof -i:5000 | grep LISTEN; then
    echo "Error: Port 5000 is already in use. Is the server already running?"
    exit 1
fi

source "$VHOSTS_BASE/news10-related-scripts/venv/bin/activate"
python3 "$VHOSTS_BASE/news10-related-scripts/webhook_server.py"
