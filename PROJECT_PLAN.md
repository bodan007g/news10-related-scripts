# News Processing Pipeline - Implementation Plan

## Current Status Analysis

### ✅ Already Implemented
- **Link Collection**: `domain_links.py` with cron job (`run_domain_links.sh`)
  - Runs every 10 minutes via cron
  - Logs organized as `logs/YYYY-MM/domain.csv` 
  - Caching system with 5-minute freshness
  - Detects new article URLs from news websites

- **BART Model Integration**: `bart_llm_utils.py`
  - Text summarization using `facebook/bart-large-cnn`
  - Zero-shot classification using `facebook/bart-large-mnli`
  - Domain classification (economic, politic, social, sport, etc.)

- **Web Scraping Utilities**: `utils.py`
  - HTML content downloading and caching
  - Link extraction from web pages
  - Basic HTML processing

- **GitHub Webhook Server**: `webhook_server.py`
  - Automated deployment via GitHub webhooks
  - HMAC signature verification for security

## Proposed Architecture

### 1. Directory Structure
```
news10-related-scripts/
├── content/YYYY-MM/website-name/
│   ├── raw/           # Original HTML files (.html)
│   ├── extracted/     # Clean article text (.md)
│   ├── metadata/      # AI-generated analysis (.yaml)
│   └── archive/       # Compressed old content (.zip)
├── extraction_rules/  # Per-website HTML extraction configs
├── rss/              # Generated RSS feeds
├── logs/YYYY-MM/     # Processing logs (existing)
├── cache/            # Temporary processing cache (existing)
└── scripts/          # All processing scripts
```

### 2. New Core Scripts with Shell Wrappers

#### **Content Fetcher** (`content_fetcher.py` + `run_content_fetcher.sh`)
- **Purpose**: Download HTML content for discovered article URLs
- **Input**: New links from `logs/YYYY-MM/domain.csv`
- **Output**: Raw HTML files in `content/YYYY-MM/website/raw/`
- **Features**:
  - Tracks processing status to avoid re-downloading
  - Handles website errors and timeouts gracefully
  - Maintains download statistics
- **Cron Schedule**: Every 15 minutes
- **Status**: 🔄 Pending Implementation

#### **Text Extractor** (`text_extractor.py` + `run_text_extractor.sh`)
- **Purpose**: Extract clean article text from HTML
- **Input**: Raw HTML files from `content/*/raw/`
- **Output**: Clean Markdown files in `content/*/extracted/`
- **Features**:
  - Generic HTML cleaning (remove scripts, ads, navigation)
  - Website-specific extraction using `extraction_rules/website.yaml`
  - Integration with `readability-lxml` for automatic content detection
  - Optional `pandoc` integration for HTML→Markdown conversion
- **Cron Schedule**: Every 20 minutes
- **Status**: 🔄 Pending Implementation

#### **AI Analyzer** (`ai_analyzer.py` + `run_ai_analyzer.sh`)
- **Purpose**: Generate metadata and analyze content using AI
- **Input**: Markdown files from `content/*/extracted/`
- **Output**: YAML metadata files in `content/*/metadata/`
- **Features**:
  - BART-based text summarization
  - Named entity extraction
  - Sentiment analysis
  - Article importance scoring for RSS filtering
  - Category classification (politics, economy, sports, accidents, etc.)
  - Location detection and geographic tagging
  - Subject complexity evaluation
- **Cron Schedule**: Every 30 minutes
- **Status**: 🔄 Pending Implementation

#### **Archive Manager** (`archive_manager.py` + `run_archive_manager.sh`)
- **Purpose**: Manage disk space and archive old content
- **Features**:
  - Compress content older than 2 months into ZIP files
  - Clean old cache files
  - Remove processed temporary files
  - Generate archive statistics
- **Cron Schedule**: Daily at 2:00 AM
- **Status**: 🔄 Pending Implementation

#### **RSS Generator** (`rss_generator.py` + `run_rss_generator.sh`)
- **Purpose**: Generate RSS feeds for processed news
- **Input**: Metadata files from `content/*/metadata/`
- **Output**: RSS feeds in `rss/` directory
- **Features**:
  - Generate feeds per website (last 10 high-importance articles)
  - Generate category-based feeds (politics, economy, local, etc.)
  - Filter out low-importance news (car accidents, brief updates)
  - Include original URL, generated summary, and tags
  - Romanian language support
- **Cron Schedule**: Every hour
- **Status**: 🔄 Pending Implementation

### 3. Configuration System

#### **Website Extraction Rules** (`extraction_rules/`)
Each website gets a YAML configuration file:
```yaml
# extraction_rules/www.bzi.ro.yaml
domain: "www.bzi.ro"
language: "ro"
article_selectors:
  - ".article-content"
  - ".post-content"
remove_selectors:
  - ".advertisement"
  - ".related-articles"
  - ".social-share"
title_selector: "h1.article-title"
date_selector: ".publish-date"
author_selector: ".author-name"
```

#### **AI Processing Configuration** (`ai_config.yaml`)
```yaml
bart_models:
  summarization: "facebook/bart-large-cnn"
  classification: "facebook/bart-large-mnli"
categories:
  - politics
  - economy
  - local
  - sports
  - accidents
  - health
  - technology
importance_thresholds:
  high: 0.8
  medium: 0.5
  low: 0.2
api_fallback:
  enabled: false
  provider: "openai"  # For future use
```

### 4. File Formats

#### **Article Metadata** (`.yaml`)
```yaml
url: "https://www.bzi.ro/article-title-5334010"
title: "Article Title Here"
summary: "AI-generated summary of the article content..."
entities:
  persons: ["Ion Popescu", "Maria Ionescu"]
  locations: ["Iași", "România"]
  organizations: ["Primăria Iași"]
sentiment: "neutral"  # positive/negative/neutral
importance_score: 0.85
categories: ["politics", "local"]
language: "ro"
word_count: 1250
complexity_score: 0.7
geographic_scope: "local"  # local/regional/national/international
processed_at: "2025-01-15T10:30:00Z"
extraction_confidence: 0.9
```

### 5. Error Handling & Monitoring System

#### **Error Management**
- Comprehensive logging per script in `logs/YYYY-MM/errors/`
- Email notifications via SendGrid for critical errors
- Retry mechanisms with exponential backoff
- Failed URL tracking and re-processing
- Health check endpoints for monitoring

#### **Monitoring Features**
- Processing statistics dashboard
- Daily/weekly summary reports
- Performance metrics (processing speed, success rates)
- Disk usage monitoring and alerts

### 6. Implementation Phases

#### **Phase 1: Core Content Pipeline** ✅ COMPLETED
- [x] ~~Link collection system~~ (Already implemented)
- [x] Content fetcher implementation
- [x] Basic text extractor with generic HTML cleaning
- [x] Shell script wrappers and cron job setup

#### **Phase 2: AI Analysis Integration** ✅ COMPLETED
- [x] AI analyzer using existing BART models
- [x] Metadata generation and storage
- [x] Website-specific extraction rules for Le Monde

#### **Phase 3: RSS and Archive Management** ✅ COMPLETED
- [x] RSS generator with importance filtering
- [x] Archive manager for old content
- [x] Website and category-based RSS feeds

#### **Phase 4: Error Handling and Monitoring** ✅ COMPLETED
- [x] Comprehensive error handling
- [x] Email notification system (SendGrid integration)
- [x] Performance monitoring and logging

#### **Phase 5: Future Enhancements** (Later)
- [ ] HTML interface for browsing processed news
- [ ] Multi-language support expansion
- [ ] API integration for advanced AI analysis
- [ ] Real-time processing optimizations

### 7. Technical Considerations

#### **Shell Script Benefits**
- Consistent virtual environment activation
- Standardized error logging
- Easy cron job management
- Environment variable handling
- Process isolation and cleanup

#### **Text Extraction Strategy**
1. Start with generic HTML cleaning using BeautifulSoup
2. Use `readability-lxml` library for automatic article detection
3. Apply website-specific CSS selectors for fine-tuning
4. Consider `pandoc` integration for HTML→Markdown conversion
5. Validate extraction quality and adjust rules iteratively

#### **Cron Schedule Summary**
- Link collection: Every 10 minutes (existing)
- Content fetching: Every 15 minutes
- Text extraction: Every 20 minutes  
- AI analysis: Every 30 minutes
- RSS generation: Every hour
- Archive management: Daily at 2 AM

### 8. Current Websites in Processing
Based on `websites.csv`:
- **www.bzi.ro** (Iași, Romania) - Local news
- **www.digi24.ro** (Bucharest, Romania) - National news  
- **www.lemonde.fr** (Paris, France) - International news

### 9. Success Metrics
- Number of articles processed per day
- Processing success rate (>95% target)
- RSS feed quality and relevance
- System uptime and reliability
- Storage efficiency through archiving

---

## 🎉 IMPLEMENTATION COMPLETE!

**All core phases have been successfully implemented:**

✅ **Content Pipeline**: Fetch → Extract → Analyze → Archive → RSS  
✅ **AI Integration**: BART summarization, classification, entity extraction  
✅ **Monitoring**: Error handling, disk usage alerts, performance tracking  
✅ **RSS Feeds**: Website-specific and category-based feeds with importance filtering  

### Ready for Production

The news processing pipeline is now fully functional and ready for cron scheduling:

```bash
# Suggested cron schedule:
*/10 * * * * /var/www/vhosts/news10-related-scripts/run_domain_links.sh
*/15 * * * * /var/www/vhosts/news10-related-scripts/run_content_fetcher.sh  
*/20 * * * * /var/www/vhosts/news10-related-scripts/run_text_extractor.sh
*/30 * * * * /var/www/vhosts/news10-related-scripts/run_ai_analyzer.sh
0 */1 * * * /var/www/vhosts/news10-related-scripts/run_rss_generator.sh
0 2 * * * /var/www/vhosts/news10-related-scripts/run_archive_manager.sh
0 */6 * * * /var/www/vhosts/news10-related-scripts/run_monitor.sh
```

**Last Updated**: 2025-09-06  
**Status**: ✅ FULLY IMPLEMENTED