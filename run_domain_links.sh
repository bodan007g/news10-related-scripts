#!/bin/bash
SCRIPT_DIR="/var/www/vhosts/news10-related-scripts"

source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR"
python3 domain_links.py
