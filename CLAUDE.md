# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Serena MCP Integration

**IMPORTANT**: This project is configured with Serena MCP for advanced code navigation and editing. Always use Serena's semantic tools for better code understanding:

### Serena Configuration
- **MCP Server**: Configured via `claude mcp add serena` 
- **Context**: `ide-assistant` (optimized for IDE integration)
- **Project**: Auto-activated for `/media/daniel-ssd/code/news10-related-scripts`
- **Indexing**: Project symbols are indexed for fast performance

### Preferred Serena Commands
Instead of basic file operations, use Serena's semantic tools:

- **Find symbols**: Use Serena to find functions, classes, methods by name or pattern
- **Navigate code**: Use Serena to show symbol definitions and references
- **Code analysis**: Use Serena to get symbol overviews and project structure
- **Editing**: Use Serena's symbol-based editing for precise modifications

### Available Serena Tools
- `find_symbol` - Search for symbols by name/pattern
- `find_referencing_symbols` - Find all references to a symbol
- `get_symbols_overview` - Get file structure overview
- `read_file` - Enhanced file reading with context
- `replace_symbol_body` - Replace entire symbol definitions
- `insert_after_symbol`/`insert_before_symbol` - Precise insertions
- `search_for_pattern` - Advanced pattern search
- `execute_shell_command` - Run commands with context

**Always prefer Serena tools over basic file operations for better accuracy and efficiency.**

## Project Overview

This is a news-related scripts repository that combines web scraping, NLP, and webhook functionality for processing news content. The main components are:

1. **BART LLM utilities** (`bart_llm_utils.py`) - Uses Facebook's BART model for zero-shot classification and text summarization
2. **Web scraping utilities** (`utils.py`, `domain_links.py`) - Downloads and processes HTML content, extracts domain links
3. **GitHub webhook server** (`webhook_server.py`) - Flask server for automated deployments via GitHub webhooks

## Development Environment

### Virtual Environment
The project uses a Python virtual environment located in `venv/`. Activate it before running any Python scripts:
```bash
source venv/bin/activate
```

### Dependencies
- `transformers` (HuggingFace) for BART models
- `flask` for webhook server
- `requests` for HTTP requests
- `beautifulsoup4` for HTML parsing
- Standard library modules: `csv`, `os`, `datetime`, `urllib.parse`, etc.

## Running Tests

Run individual test files:
```bash
python3 test_bart_llm_utils.py
python3 test_utils.py
```

Note: BART model tests require internet connectivity and will download models on first run.

## Key Architecture

### BART LLM Integration
- `bart_summarize_text()` - Uses `facebook/bart-large-cnn` for text summarization
- `detect_domain_from_link()` - Uses `facebook/bart-large-mnli` for zero-shot classification into predefined domains (economic, politic, social, sport, etc.)

### Web Scraping Pipeline
- `domain_links.py` - Main script that processes websites from `websites.csv`
- Caching system in `cache/` directory (5-minute freshness threshold)
- Logging system in `logs/` with monthly organization
- Extracts internal links from websites and tracks new discoveries

### Webhook Server
- Flask server on port 5000 for GitHub webhook integration
- HMAC signature verification for security
- Supports multiple projects via URL routing (`/webhook/<project>`)
- Executes `git pull` on push events

## File Structure

- `bart_llm_utils.py` - BART model utilities
- `utils.py` - HTML processing and caching utilities  
- `domain_links.py` - Main link extraction script
- `webhook_server.py` - GitHub webhook server
- `websites.csv` - Input file with websites to monitor
- `test_*.py` - Unit tests
- `cache/` - HTML cache directory
- `logs/` - Monthly organized logs with CSV per domain

## Security Notes

- GitHub webhook secret is hardcoded in `webhook_server.py` (line 8)
- HMAC signature verification implemented for webhook security
- HTML content is sanitized by removing script/style tags and most attributes

## Common Workflows

1. **Add new website to monitor**: Edit `websites.csv` and run `python3 domain_links.py`
2. **Test BART functionality**: Use functions from `bart_llm_utils.py` directly or run the module
3. **Deploy webhook server**: Run `python3 webhook_server.py` (typically as a service)