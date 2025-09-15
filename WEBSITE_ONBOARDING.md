# Website Onboarding Tool Documentation

## Overview

The Website Onboarding Tool (`website_onboarder.py`) is an automated system that analyzes news websites and generates YAML configuration files for the text extraction pipeline. This tool eliminates the manual process of creating extraction rules by intelligently analyzing website structure and content patterns.

## Table of Contents

1. [Quick Start](#quick-start)
2. [How It Works](#how-it-works)
3. [Architecture](#architecture)
4. [Configuration Format](#configuration-format)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)
7. [Manual Refinement](#manual-refinement)
8. [Integration with Existing Pipeline](#integration-with-existing-pipeline)

## Quick Start

### Basic Usage

```bash
# Onboard a new website
python3 website_onboarder.py https://example-news.com

# Generated files:
# - extraction_rules/example-news.com.yaml (configuration)
# - onboarding_reports/example-news.com_analysis_20240315_143022.json (analysis report)
```

### Test the Generated Configuration

```bash
# Test with trafilatura
./run_text_extractor.sh 5 trafilatura --domain example-news.com

# Test with newspaper3k  
./run_text_extractor.sh 5 newspaper --domain example-news.com
```

## How It Works

The onboarding process consists of five main phases:

### 1. Article Discovery 🔍

The tool discovers article URLs using multiple strategies:

- **RSS Feed Detection**: Checks common RSS paths (`/rss`, `/feed`, `/rss.xml`, etc.)
- **Sitemap Parsing**: Parses `robots.txt` and XML sitemaps for article URLs
- **Homepage Crawling**: Extracts article links from homepage and category pages
- **URL Filtering**: Applies heuristics to distinguish articles from other content

### 2. Article Analysis 🔬

Downloads and analyzes 10 sample articles to identify:

- **Title Patterns**: `h1`, `.title`, `.headline` selectors with scoring
- **Subtitle Patterns**: `h2`, `.subtitle`, `.deck`, meta descriptions
- **Author Patterns**: `.author`, `.byline`, `.by-author` selectors
- **Content Areas**: `.article-content`, `.post-content`, main content containers
- **Boilerplate Elements**: Navigation, ads, social sharing, comments
- **Language Detection**: Automatic language identification for cleanup patterns

### 3. Pattern Aggregation ⚙️

Aggregates findings across all sample articles:

- **Selector Scoring**: Ranks selectors by reliability and frequency
- **Common Elements**: Identifies consistently appearing structural elements
- **Text Patterns**: Detects repeated boilerplate text for removal
- **Language-Specific Rules**: Applies appropriate cleanup patterns

### 4. YAML Generation 📄

Creates a complete configuration file with:

- **Content Filters**: URL patterns, article ID requirements, word count limits
- **Extraction Rules**: Article selectors, removal patterns, metadata selectors
- **Cleanup Patterns**: Language-specific text cleaning rules
- **Custom Sections**: Enhanced title/subtitle/author extraction

### 5. Validation ✅

Tests the generated configuration:

- **Extraction Testing**: Validates selectors against sample articles
- **Quality Metrics**: Measures content extraction success rate
- **Issue Detection**: Identifies potential problems and provides recommendations

## Architecture

### Core Classes

#### `WebsiteOnboarder`

Main orchestrator class that manages the entire onboarding process.

```python
class WebsiteOnboarder:
    def __init__(self, base_url: str, sample_size: int = 10)
    def discover_articles(self) -> List[str]
    def analyze_articles(self, urls: List[str]) -> Dict
    def generate_yaml_config(self, analysis: Dict) -> str
    def validate_config(self, yaml_config: str) -> Dict
    def run(self) -> Tuple[str, str]
```

### Key Methods

#### Article Discovery

- `_discover_rss_feeds()`: Finds RSS/Atom feeds
- `_discover_sitemaps()`: Locates and parses XML sitemaps
- `_crawl_homepage_for_articles()`: Extracts links from homepage
- `_looks_like_article_url()`: Filters article URLs using heuristics

#### Structure Analysis

- `_analyze_single_article()`: Analyzes one article's HTML structure
- `_find_title_candidates()`: Identifies potential title elements
- `_find_content_candidates()`: Locates main content areas
- `_aggregate_analysis()`: Combines results from all articles

#### Configuration Generation

- `_generate_article_selectors()`: Creates content area selectors
- `_generate_cleanup_patterns()`: Builds language-specific cleanup rules
- `_generate_custom_sections()`: Configures enhanced extraction sections

### Dependencies

- **BeautifulSoup4**: HTML parsing and DOM analysis
- **requests**: HTTP client for downloading content
- **feedparser**: RSS/Atom feed parsing
- **PyYAML**: YAML configuration generation
- **Existing utilities**: Leverages `utils.py` and `text_cleanup.py`

## Configuration Format

The generated YAML files follow the established extraction rules format:

### Structure Overview

```yaml
domain: "example-news.com"
language: "en"

# URL-based content filtering
content_filters:
  require_article_id: true
  article_id_pattern: '-(\d{4,})(?:\.html?)?$'
  min_word_count: 150
  additional_skip_patterns: [...]

# HTML extraction rules  
article_selectors: [...]
remove_selectors: [...]
title_selector: "h1"
date_selector: ".date, time"
author_selector: ".author, .byline"

# Text cleanup patterns
cleanup_patterns:
  subscription_walls: [...]
  navigation_elements: [...]
  social_sharing: [...]
  boilerplate_removal: [...]

# Enhanced extraction sections
custom_content_sections:
  enabled: true
  sections: [...]
  processing_options: {...}
```

### Content Filters

Controls which URLs and content to process:

```yaml
content_filters:
  require_article_id: true                    # Require article IDs in URLs
  article_id_pattern: '-(\d{4,})(?:\.html?)?$'  # Regex for article ID detection
  min_word_count: 150                         # Minimum article length
  additional_skip_patterns:                   # URL patterns to skip
    - '/tag/'
    - '/category/'
    - '/author/'
```

### HTML Selectors

Define how to extract content from HTML:

```yaml
article_selectors:                           # Main content areas (in priority order)
  - ".article-content"
  - ".post-content"  
  - "article"

remove_selectors:                           # Elements to remove
  - ".advertisement"
  - ".social-share"
  - ".navigation"

title_selector: "h1"                        # Article title
author_selector: ".author, .byline"        # Author information
date_selector: ".date, time"               # Publication date
```

### Cleanup Patterns

Language-specific text processing rules:

```yaml
cleanup_patterns:
  subscription_walls:                       # Paywall/subscription text
    - "Read more.*subscription.*"
    - "This article is for subscribers.*"
    
  navigation_elements:                      # Navigation text
    - "Read more.*"
    - "See also.*"
    
  boilerplate_removal:                     # Common boilerplate
    - "Follow.*?on Twitter.*"
    - "Share this article.*"
```

### Custom Content Sections

Enhanced extraction for titles, subtitles, and authors:

```yaml
custom_content_sections:
  enabled: true
  sections:
    - name: "title"
      selectors: ["h1.article-title", ".headline h1"]
      fallback_selectors: ["h1", "title"]
      format: "# {content}"
      order: 1
      
    - name: "subtitle"  
      selectors: [".subtitle", ".deck", ".lead"]
      fallback_selectors: ["meta[name='description']"]
      format: "## {content}"
      order: 2
```

## Usage Examples

### Basic Website Onboarding

```bash
# French news site
python3 website_onboarder.py https://www.lemonde.fr

# Romanian news site  
python3 website_onboarder.py https://www.bzi.ro

# English news site
python3 website_onboarder.py https://www.bbc.com/news
```

### Custom Sample Size

```python
# Analyze more articles for better accuracy
onboarder = WebsiteOnboarder("https://example.com", sample_size=20)
config_path, report_path = onboarder.run()
```

### Integration with Existing Pipeline

```bash
# 1. Onboard the website
python3 website_onboarder.py https://news-site.com

# 2. Test the configuration
./run_text_extractor.sh 5 trafilatura --domain news-site.com

# 3. Review results and refine if needed
# Edit extraction_rules/news-site.com.yaml

# 4. Run full extraction
./run_text_extractor.sh 50 trafilatura --domain news-site.com
```

## Output Files

### Generated Configuration

**Location**: `extraction_rules/{domain}.yaml`

Complete extraction configuration ready for production use.

### Analysis Report

**Location**: `onboarding_reports/{domain}_analysis_{timestamp}.json`

Detailed analysis including:

```json
{
  "domain": "example.com",
  "timestamp": "20240315_143022",
  "sample_articles": ["url1", "url2", ...],
  "analysis": {
    "successful_downloads": 8,
    "title_patterns": [...],
    "subtitle_patterns": [...],
    "language": "en",
    "common_classes": {...}
  },
  "validation": {
    "successful_extractions": 7,
    "failed_extractions": 1,
    "average_word_count": 425,
    "issues": [...]
  }
}
```

## Troubleshooting

### Common Issues

#### 1. No Articles Found

**Problem**: `No articles found for analysis`

**Solutions**:
- Check if the website URL is accessible
- Verify the site has RSS feeds or recent articles
- Try a direct article URL instead of homepage

```bash
# Debug article discovery
python3 -c "
from website_onboarder import WebsiteOnboarder
onboarder = WebsiteOnboarder('https://example.com')
urls = onboarder.discover_articles()
print(f'Found {len(urls)} articles:', urls[:5])
"
```

#### 2. Poor Extraction Quality

**Problem**: Low validation success rate

**Solutions**:
- Increase sample size for better pattern detection
- Manually review and refine generated selectors
- Check for dynamic content loading (JavaScript)

#### 3. Language Detection Issues

**Problem**: Wrong language detected

**Solutions**:
- Manually edit the `language` field in generated YAML
- Review and adjust language-specific cleanup patterns
- Check HTML `lang` attribute on the website

#### 4. Missing Content

**Problem**: Important content not extracted

**Solutions**:
- Review `article_selectors` and add missing patterns
- Check `remove_selectors` for overly broad rules
- Enable custom sections for enhanced extraction

### Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

onboarder = WebsiteOnboarder("https://example.com")
# Will show detailed analysis information
```

### Manual Inspection

Examine intermediate results:

```python
onboarder = WebsiteOnboarder("https://example.com")
articles = onboarder.discover_articles()
analysis = onboarder.analyze_articles(articles)

# Inspect specific patterns
print("Title patterns:", analysis['title_patterns'])
print("Content patterns:", analysis['content_patterns'])
```

## Manual Refinement

The generated configuration provides a solid foundation but may need refinement:

### Common Refinements

#### 1. Selector Optimization

Review and refine selectors based on test results:

```yaml
# Before (generic)
article_selectors:
  - ".content"
  - "article"

# After (site-specific)  
article_selectors:
  - ".article-body .text-content"
  - ".main-content .story-body"
```

#### 2. Cleanup Pattern Enhancement

Add site-specific boilerplate patterns:

```yaml
cleanup_patterns:
  boilerplate_removal:
    - "Follow.*ExampleNews.*on Twitter"
    - "Subscribe to our.*newsletter"
    - "© 2024 Example News.*All rights reserved"
```

#### 3. Custom Section Tuning

Fine-tune custom extraction sections:

```yaml
custom_content_sections:
  sections:
    - name: "title"
      selectors:
        - "h1.story-headline"        # Site-specific title
        - ".article-header h1"
      # Remove generic fallbacks that don't work well
```

#### 4. Content Filter Adjustment

Refine URL filtering patterns:

```yaml
content_filters:
  article_id_pattern: '/news/(\d{4})/(\d{2})/(\d{2})/([^/]+)-(\d+)\.html$'
  additional_skip_patterns:
    - '/live-blog/'               # Site-specific patterns
    - '/photo-gallery/'
    - '/video/'
```

### Testing Refinements

After making changes, test thoroughly:

```bash
# Test specific domain
./run_text_extractor.sh 10 trafilatura --domain example.com

# Compare before/after results
diff extraction_rules/example.com.yaml.backup extraction_rules/example.com.yaml
```

### Iterative Improvement

1. **Generate initial configuration**
2. **Test on sample articles**
3. **Identify issues** (missing content, wrong selectors, etc.)
4. **Refine configuration**
5. **Test again**
6. **Repeat until satisfied**

## Integration with Existing Pipeline

### Directory Structure

```
news10-related-scripts/
├── website_onboarder.py           # New onboarding tool
├── extraction_rules/              # Configuration files
│   ├── www.example.com.yaml       # Generated configurations
│   └── ...
├── onboarding_reports/            # Analysis reports
│   ├── example.com_analysis_*.json
│   └── ...
└── existing files...
```

### Workflow Integration

#### 1. New Website Setup

```bash
# Traditional manual approach (old way)
# 1. Manually analyze website structure
# 2. Create YAML file by hand  
# 3. Test and refine

# Automated approach (new way)
python3 website_onboarder.py https://new-site.com
./run_text_extractor.sh 10 trafilatura --domain new-site.com
# Review and refine as needed
```

#### 2. Existing Website Updates

Use the onboarding tool to refresh configurations for existing sites:

```bash
# Backup current config
cp extraction_rules/site.com.yaml extraction_rules/site.com.yaml.backup

# Generate new config
python3 website_onboarder.py https://site.com

# Compare and merge changes
diff extraction_rules/site.com.yaml.backup extraction_rules/site.com.yaml
```

#### 3. Bulk Onboarding

Script multiple websites:

```bash
#!/bin/bash
websites=(
    "https://site1.com"
    "https://site2.com" 
    "https://site3.com"
)

for site in "${websites[@]}"; do
    echo "Onboarding $site..."
    python3 website_onboarder.py "$site"
    
    # Extract domain for testing
    domain=$(echo "$site" | sed 's|https\?://||' | sed 's|www\.||' | cut -d'/' -f1)
    
    # Quick test
    ./run_text_extractor.sh 3 trafilatura --domain "$domain"
done
```

### Continuous Improvement

#### 1. Regular Re-analysis

Websites change their structure over time. Re-run onboarding periodically:

```bash
# Monthly re-analysis
crontab -e
# Add: 0 2 1 * * /path/to/reanalyze_websites.sh
```

#### 2. Performance Monitoring

Track extraction quality over time:

```bash
# Monitor extraction success rates
./run_text_extractor.sh 20 trafilatura --domain site.com | grep -E "(✅|❌)"
```

#### 3. Feedback Loop

Use extraction results to improve onboarding:

- Analyze failed extractions
- Identify common patterns
- Update onboarding algorithms
- Regenerate configurations

## Advanced Features

### Custom Analysis

Extend the onboarding tool for specific requirements:

```python
class CustomOnboarder(WebsiteOnboarder):
    def _find_title_candidates(self, soup):
        # Custom title detection logic
        candidates = super()._find_title_candidates(soup)
        
        # Add site-specific patterns
        custom_selectors = [
            ('.main-headline', 3.0),
            ('[data-title]', 2.5)
        ]
        
        for selector, score in custom_selectors:
            elements = soup.select(selector)
            for elem in elements:
                # Add to candidates...
        
        return candidates
```

### Integration with External Tools

```python
# Save results to database
def save_to_database(domain, config, analysis):
    # Database integration code
    pass

# Send notifications
def notify_completion(domain, success):
    # Slack/email notification code
    pass
```

### Batch Processing

```python
# Process multiple sites
sites = ['site1.com', 'site2.com', 'site3.com']

for site in sites:
    try:
        onboarder = WebsiteOnboarder(f"https://{site}")
        config_path, report_path = onboarder.run()
        print(f"✅ {site}: {config_path}")
    except Exception as e:
        print(f"❌ {site}: {e}")
```

## Best Practices

### 1. Quality Over Quantity

- Start with 10 representative articles
- Increase sample size if patterns are inconsistent
- Focus on recent articles (site structure may have changed)

### 2. Language Considerations

- Ensure proper language detection
- Review language-specific cleanup patterns
- Test with multilingual content if applicable

### 3. Validation and Testing

- Always test generated configurations
- Use diverse article samples
- Compare results with manual extraction

### 4. Documentation and Maintenance

- Document any manual refinements
- Keep onboarding reports for future reference
- Version control configuration changes

### 5. Security and Rate Limiting

- Respect robots.txt
- Add delays between requests
- Use appropriate User-Agent strings
- Handle rate limiting gracefully

## Contributing

### Adding New Features

1. **Article Discovery**: Add new methods for finding articles
2. **Analysis Algorithms**: Improve pattern detection accuracy
3. **Language Support**: Add new language-specific patterns
4. **Output Formats**: Support additional configuration formats

### Code Structure

```python
# Follow existing patterns
class NewFeature:
    def __init__(self, onboarder: WebsiteOnboarder):
        self.onboarder = onboarder
    
    def analyze(self) -> Dict:
        # Implementation
        pass
```

### Testing

```bash
# Test with known websites
python3 website_onboarder.py https://www.lemonde.fr
python3 website_onboarder.py https://www.bzi.ro

# Verify output quality
./run_text_extractor.sh 5 trafilatura --domain lemonde.fr
```

---

## Conclusion

The Website Onboarding Tool significantly reduces the manual effort required to configure new websites for text extraction. By automating the analysis of website structure and generating comprehensive YAML configurations, it enables rapid deployment of new news sources while maintaining extraction quality.

The tool's modular design allows for customization and extension, while its integration with the existing text extraction pipeline ensures seamless operation within the broader news processing system.

For questions, issues, or contributions, please refer to the main project documentation or create an issue in the project repository.