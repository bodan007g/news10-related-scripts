#!/bin/bash
# Start the multi-project webhook server in production mode
export SERVER_ENV=production
VHOSTS_BASE="/var/www/vhosts"
python3 "$VHOSTS_BASE/news10-related-scripts/webhook_server.py"
