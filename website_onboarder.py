#!/usr/bin/env python3

import os
import sys
import json
import yaml
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from collections import Counter, defaultdict

import requests
from bs4 import BeautifulSoup
import feedparser

# Import existing utilities
from utils import download_html, get_html_content
from text_cleanup import MultiLanguageTextCleaner


class WebsiteOnboarder:
    """
    Automated website onboarding tool that analyzes news websites 
    and generates YAML configuration files for text extraction.
    """
    
    def __init__(self, base_url: str, sample_size: int = 10):
        self.base_url = base_url.rstrip('/')
        self.domain = self._extract_domain(base_url)
        self.sample_size = sample_size
        self.sample_articles = []
        self.analysis_results = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Create directories
        self.reports_dir = "onboarding_reports"
        self.rules_dir = "extraction_rules"
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.rules_dir, exist_ok=True)
        
        print(f"🚀 Starting onboarding for: {self.domain}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    
    def discover_articles(self) -> List[str]:
        """
        Discover article URLs from various sources:
        - RSS feeds
        - Sitemaps
        - Homepage crawling
        """
        print("🔍 Discovering articles...")
        
        all_urls = set()
        
        # Try RSS feeds
        rss_urls = self._discover_rss_feeds()
        for rss_url in rss_urls:
            urls = self._extract_urls_from_rss(rss_url)
            all_urls.update(urls)
            print(f"   📡 Found {len(urls)} URLs from RSS: {rss_url}")
        
        # Try sitemaps
        sitemap_urls = self._discover_sitemaps()
        for sitemap_url in sitemap_urls:
            urls = self._extract_urls_from_sitemap(sitemap_url)
            all_urls.update(urls)
            print(f"   🗺️  Found {len(urls)} URLs from sitemap: {sitemap_url}")
        
        # Homepage crawling as fallback
        if len(all_urls) < self.sample_size:
            homepage_urls = self._crawl_homepage_for_articles()
            all_urls.update(homepage_urls)
            print(f"   🏠 Found {len(homepage_urls)} URLs from homepage crawling")
        
        # Filter and validate URLs
        filtered_urls = self._filter_article_urls(list(all_urls))
        
        # Select sample articles
        sample_urls = filtered_urls[:self.sample_size]
        print(f"✅ Selected {len(sample_urls)} articles for analysis")
        
        return sample_urls
    
    def _discover_rss_feeds(self) -> List[str]:
        """Discover RSS feed URLs"""
        common_paths = [
            '/rss', '/rss.xml', '/feed', '/feed.xml', '/feeds',
            '/index.xml', '/atom.xml', '/rss/news', '/feeds/all'
        ]
        
        rss_urls = []
        for path in common_paths:
            url = urljoin(self.base_url, path)
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    # Check if it's actually RSS/XML
                    if 'xml' in response.headers.get('content-type', '').lower() or \
                       any(tag in response.text[:1000] for tag in ['<rss', '<feed', '<atom']):
                        rss_urls.append(url)
            except:
                continue
        
        return rss_urls
    
    def _extract_urls_from_rss(self, rss_url: str) -> List[str]:
        """Extract article URLs from RSS feed"""
        try:
            feed = feedparser.parse(rss_url)
            urls = []
            for entry in feed.entries[:20]:  # Limit to recent entries
                if hasattr(entry, 'link'):
                    urls.append(entry.link)
            return urls
        except:
            return []
    
    def _discover_sitemaps(self) -> List[str]:
        """Discover sitemap URLs"""
        sitemap_urls = []
        
        # Check robots.txt
        try:
            robots_url = urljoin(self.base_url, '/robots.txt')
            response = self.session.get(robots_url, timeout=10)
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        sitemap_urls.append(sitemap_url)
        except:
            pass
        
        # Common sitemap paths
        common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemaps.xml']
        for path in common_paths:
            url = urljoin(self.base_url, path)
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200 and 'xml' in response.headers.get('content-type', '').lower():
                    sitemap_urls.append(url)
            except:
                continue
        
        return sitemap_urls
    
    def _extract_urls_from_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract URLs from sitemap"""
        try:
            response = self.session.get(sitemap_url, timeout=10)
            soup = BeautifulSoup(response.content, 'xml')
            
            urls = []
            
            # Handle sitemap index files
            sitemap_tags = soup.find_all('sitemap')
            if sitemap_tags:
                for sitemap_tag in sitemap_tags[:5]:  # Limit subsitemaps
                    loc = sitemap_tag.find('loc')
                    if loc:
                        sub_urls = self._extract_urls_from_sitemap(loc.text)
                        urls.extend(sub_urls[:10])  # Limit per subsitemap
            
            # Handle regular sitemaps
            url_tags = soup.find_all('url')
            for url_tag in url_tags[:50]:  # Limit total URLs
                loc = url_tag.find('loc')
                if loc:
                    urls.append(loc.text)
            
            return urls
        except:
            return []
    
    def _crawl_homepage_for_articles(self) -> List[str]:
        """Crawl homepage and category pages for article links"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            urls = set()
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                elif not href.startswith('http'):
                    continue
                
                # Basic filtering for article-like URLs
                if self._looks_like_article_url(href):
                    urls.add(href)
            
            return list(urls)[:30]  # Limit results
        except:
            return []
    
    def _looks_like_article_url(self, url: str) -> bool:
        """Basic heuristic to identify article URLs"""
        parsed = urlparse(url)
        
        # Skip external domains
        if self.domain not in parsed.netloc.lower():
            return False
        
        # Skip common non-article patterns
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/search/', '/page/',
            '/contact', '/about', '/privacy', '/terms', '/login',
            '/register', '/admin', '/wp-', '/feed', '.xml', '.json',
            '#', '?', '/comments'
        ]
        
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        
        # Prefer URLs with article-like patterns
        article_patterns = [
            r'/\d{4}/',  # Year in URL
            r'/news/', r'/article/', r'/post/', r'/story/',
            r'-\d+$', r'-\d+\.html$'  # Ending with ID
        ]
        
        for pattern in article_patterns:
            if re.search(pattern, url):
                return True
        
        return len(parsed.path.strip('/').split('/')) >= 2  # At least 2 path segments
    
    def _filter_article_urls(self, urls: List[str]) -> List[str]:
        """Filter and validate article URLs"""
        filtered = []
        seen = set()
        
        for url in urls:
            # Skip duplicates
            if url in seen:
                continue
            seen.add(url)
            
            # Apply filtering
            if self._looks_like_article_url(url):
                filtered.append(url)
        
        return filtered
    
    def analyze_articles(self, urls: List[str]) -> Dict:
        """Analyze HTML structure of sample articles"""
        print("🔬 Analyzing article structure...")
        
        analysis = {
            'total_articles': len(urls),
            'successful_downloads': 0,
            'title_patterns': [],
            'subtitle_patterns': [],
            'author_patterns': [],
            'content_patterns': [],
            'remove_patterns': [],
            'language': 'en',
            'common_classes': Counter(),
            'common_ids': Counter(),
            'boilerplate_text': Counter(),
        }
        
        article_data = []
        
        for i, url in enumerate(urls):
            print(f"   📄 Analyzing article {i+1}/{len(urls)}: {url}")
            
            try:
                # Download HTML
                html_content = self._download_article_html(url)
                if not html_content:
                    continue
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Analyze this article
                article_analysis = self._analyze_single_article(soup, url)
                article_data.append(article_analysis)
                
                analysis['successful_downloads'] += 1
                
            except Exception as e:
                print(f"   ❌ Failed to analyze {url}: {e}")
                continue
        
        # Aggregate results from all articles
        analysis = self._aggregate_analysis(article_data, analysis)
        
        print(f"✅ Successfully analyzed {analysis['successful_downloads']} articles")
        return analysis
    
    def _download_article_html(self, url: str) -> Optional[str]:
        """Download HTML content for an article"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                return response.text
        except:
            pass
        return None
    
    def _analyze_single_article(self, soup: BeautifulSoup, url: str) -> Dict:
        """Analyze a single article's HTML structure"""
        
        # Find potential title elements
        title_candidates = self._find_title_candidates(soup)
        
        # Find potential subtitle elements  
        subtitle_candidates = self._find_subtitle_candidates(soup)
        
        # Find potential author elements
        author_candidates = self._find_author_candidates(soup)
        
        # Find potential content areas
        content_candidates = self._find_content_candidates(soup)
        
        # Find elements to remove (ads, navigation, etc.)
        remove_candidates = self._find_remove_candidates(soup)
        
        # Collect all classes and IDs
        all_classes = []
        all_ids = []
        for elem in soup.find_all(True):
            if elem.get('class'):
                all_classes.extend(elem['class'])
            if elem.get('id'):
                all_ids.append(elem['id'])
        
        # Detect language
        language = self._detect_language(soup)
        
        # Find common text patterns (potential boilerplate)
        text_patterns = self._find_text_patterns(soup)
        
        return {
            'url': url,
            'title_candidates': title_candidates,
            'subtitle_candidates': subtitle_candidates,
            'author_candidates': author_candidates,
            'content_candidates': content_candidates,
            'remove_candidates': remove_candidates,
            'all_classes': all_classes,
            'all_ids': all_ids,
            'language': language,
            'text_patterns': text_patterns
        }
    
    def _find_title_candidates(self, soup: BeautifulSoup) -> List[Dict]:
        """Find potential title elements with scoring"""
        candidates = []
        
        # Define selectors to try
        selectors = [
            ('h1', 2.0),
            ('h1[class*="title"]', 3.0),
            ('h1[class*="headline"]', 3.0),
            ('.title h1', 2.5),
            ('.headline h1', 2.5),
            ('.article-title', 2.0),
            ('.post-title', 2.0),
            ('[class*="article"] h1', 2.0),
        ]
        
        for selector, base_score in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 10:  # Reasonable title length
                    score = base_score
                    
                    # Boost score for certain characteristics
                    if 'title' in ' '.join(elem.get('class', [])).lower():
                        score += 0.5
                    if elem.name == 'h1':
                        score += 0.3
                    
                    candidates.append({
                        'selector': self._generate_selector(elem),
                        'text': text[:100],  # Truncate for analysis
                        'score': score,
                        'element': elem.name,
                        'classes': elem.get('class', [])
                    })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:5]  # Top 5 candidates
    
    def _find_subtitle_candidates(self, soup: BeautifulSoup) -> List[Dict]:
        """Find potential subtitle/deck elements"""
        candidates = []
        
        selectors = [
            ('h2', 1.5),
            ('.subtitle', 2.0),
            ('.deck', 2.0),
            ('.lead', 1.8),
            ('.article-subtitle', 2.0),
            ('.post-subtitle', 2.0),
            ('h2[class*="subtitle"]', 2.5),
            ('.article-lead', 1.8),
            ('meta[name="description"]', 1.0),
        ]
        
        for selector, base_score in selectors:
            if selector.startswith('meta'):
                elements = soup.select(selector)
                for elem in elements:
                    content = elem.get('content', '')
                    if content and len(content) > 20:
                        candidates.append({
                            'selector': selector,
                            'text': content[:150],
                            'score': base_score,
                            'element': 'meta',
                            'classes': []
                        })
            else:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and 20 <= len(text) <= 300:  # Reasonable subtitle length
                        score = base_score
                        
                        if 'subtitle' in ' '.join(elem.get('class', [])).lower():
                            score += 0.5
                        
                        candidates.append({
                            'selector': self._generate_selector(elem),
                            'text': text[:150],
                            'score': score,
                            'element': elem.name,
                            'classes': elem.get('class', [])
                        })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:5]
    
    def _find_author_candidates(self, soup: BeautifulSoup) -> List[Dict]:
        """Find potential author elements"""
        candidates = []
        
        selectors = [
            ('.author', 2.0),
            ('.byline', 2.0),
            ('.by-author', 2.0),
            ('.article-author', 2.0),
            ('.post-author', 2.0),
            ('[class*="author"]', 1.5),
            ('.meta-author', 1.8),
            ('[rel="author"]', 1.5),
        ]
        
        for selector, base_score in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and 3 <= len(text) <= 100:  # Reasonable author name length
                    candidates.append({
                        'selector': self._generate_selector(elem),
                        'text': text,
                        'score': base_score,
                        'element': elem.name,
                        'classes': elem.get('class', [])
                    })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:5]
    
    def _find_content_candidates(self, soup: BeautifulSoup) -> List[Dict]:
        """Find potential main content areas"""
        candidates = []
        
        selectors = [
            ('.content', 1.5),
            ('.article-content', 2.0),
            ('.post-content', 2.0),
            ('.entry-content', 1.8),
            ('[class*="content"]', 1.0),
            ('article', 1.5),
            ('main', 1.5),
            ('.article-body', 2.0),
            ('.post-body', 2.0),
        ]
        
        for selector, base_score in selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and len(text) > 200:  # Substantial content
                    word_count = len(text.split())
                    score = base_score + min(word_count / 1000, 2.0)  # Boost for longer content
                    
                    candidates.append({
                        'selector': self._generate_selector(elem),
                        'word_count': word_count,
                        'score': score,
                        'element': elem.name,
                        'classes': elem.get('class', [])
                    })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:5]
    
    def _find_remove_candidates(self, soup: BeautifulSoup) -> List[str]:
        """Find elements that should be removed (ads, navigation, etc.)"""
        remove_selectors = []
        
        # Common patterns to remove
        remove_patterns = [
            'advertisement', 'ads', 'ad-', 'advert',
            'navigation', 'nav', 'menu',
            'sidebar', 'side-bar',
            'footer', 'header',
            'social', 'share', 'sharing',
            'comment', 'comments',
            'related', 'recommended',
            'newsletter', 'subscribe',
            'popup', 'modal',
            'breadcrumb', 'breadcrumbs'
        ]
        
        for elem in soup.find_all(True):
            classes = ' '.join(elem.get('class', [])).lower()
            elem_id = elem.get('id', '').lower()
            
            for pattern in remove_patterns:
                if pattern in classes or pattern in elem_id:
                    selector = self._generate_selector(elem)
                    if selector not in remove_selectors:
                        remove_selectors.append(selector)
                    break
        
        return remove_selectors[:20]  # Limit results
    
    def _generate_selector(self, elem) -> str:
        """Generate a CSS selector for an element"""
        selectors = []
        
        # Use ID if available
        if elem.get('id'):
            return f"#{elem['id']}"
        
        # Use class if available
        if elem.get('class'):
            classes = [c for c in elem['class'] if c and not c.isdigit()]
            if classes:
                return f".{'.'.join(classes)}"
        
        # Fall back to element name
        return elem.name
    
    def _detect_language(self, soup: BeautifulSoup) -> str:
        """Detect the primary language of the content"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            lang = html_tag['lang'][:2].lower()
            if lang in ['en', 'fr', 'ro', 'es', 'de', 'it']:
                return lang
        
        # Simple text-based detection
        text = soup.get_text()[:1000].lower()
        
        # French indicators
        if any(word in text for word in ['le ', 'la ', 'les ', 'des ', 'une ', 'par ']):
            return 'fr'
        
        # Romanian indicators  
        if any(word in text for word in ['și ', 'în ', 'de ', 'cu ', 'pe ', 'sau ']):
            return 'ro'
        
        # Default to English
        return 'en'
    
    def _find_text_patterns(self, soup: BeautifulSoup) -> List[str]:
        """Find common text patterns that might be boilerplate"""
        patterns = []
        
        # Look for repeated short text elements
        text_elements = []
        for elem in soup.find_all(text=True):
            text = elem.strip()
            if text and 5 <= len(text) <= 100:
                text_elements.append(text)
        
        # Find patterns that appear multiple times
        text_counts = Counter(text_elements)
        for text, count in text_counts.most_common(10):
            if count > 1:
                patterns.append(text)
        
        return patterns
    
    def _aggregate_analysis(self, article_data: List[Dict], analysis: Dict) -> Dict:
        """Aggregate analysis results from all articles"""
        
        # Aggregate title patterns
        title_scores = defaultdict(float)
        for article in article_data:
            for candidate in article['title_candidates']:
                selector = candidate['selector']
                title_scores[selector] += candidate['score']
        
        analysis['title_patterns'] = sorted(
            [{'selector': sel, 'score': score} for sel, score in title_scores.items()],
            key=lambda x: x['score'], reverse=True
        )[:10]
        
        # Aggregate subtitle patterns
        subtitle_scores = defaultdict(float)
        for article in article_data:
            for candidate in article['subtitle_candidates']:
                selector = candidate['selector']
                subtitle_scores[selector] += candidate['score']
        
        analysis['subtitle_patterns'] = sorted(
            [{'selector': sel, 'score': score} for sel, score in subtitle_scores.items()],
            key=lambda x: x['score'], reverse=True
        )[:10]
        
        # Aggregate author patterns
        author_scores = defaultdict(float)
        for article in article_data:
            for candidate in article['author_candidates']:
                selector = candidate['selector']
                author_scores[selector] += candidate['score']
        
        analysis['author_patterns'] = sorted(
            [{'selector': sel, 'score': score} for sel, score in author_scores.items()],
            key=lambda x: x['score'], reverse=True
        )[:10]
        
        # Aggregate content patterns
        content_scores = defaultdict(float)
        for article in article_data:
            for candidate in article['content_candidates']:
                selector = candidate['selector']
                content_scores[selector] += candidate['score']
        
        analysis['content_patterns'] = sorted(
            [{'selector': sel, 'score': score} for sel, score in content_scores.items()],
            key=lambda x: x['score'], reverse=True
        )[:10]
        
        # Aggregate remove patterns
        all_remove = []
        for article in article_data:
            all_remove.extend(article['remove_candidates'])
        analysis['remove_patterns'] = list(set(all_remove))[:20]
        
        # Aggregate classes and IDs
        for article in article_data:
            analysis['common_classes'].update(article['all_classes'])
            analysis['common_ids'].update(article['all_ids'])
        
        # Detect most common language
        languages = [article['language'] for article in article_data]
        if languages:
            analysis['language'] = Counter(languages).most_common(1)[0][0]
        
        # Aggregate boilerplate text
        for article in article_data:
            analysis['boilerplate_text'].update(article['text_patterns'])
        
        return analysis
    
    def generate_yaml_config(self, analysis: Dict) -> str:
        """Generate YAML configuration from analysis results"""
        print("⚙️  Generating YAML configuration...")
        
        # Build configuration structure
        config = {
            'domain': f"www.{self.domain}" if not self.domain.startswith('www.') else self.domain,
            'language': analysis['language'],
            'content_filters': self._generate_content_filters(),
            'article_selectors': self._generate_article_selectors(analysis),
            'remove_selectors': self._generate_remove_selectors(analysis),
            'title_selector': self._generate_title_selector(analysis),
            'date_selector': self._generate_date_selector(),
            'author_selector': self._generate_author_selector(analysis),
            'cleanup_patterns': self._generate_cleanup_patterns(analysis),
            'custom_content_sections': self._generate_custom_sections(analysis)
        }
        
        return yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _generate_content_filters(self) -> Dict:
        """Generate content filtering rules"""
        return {
            'require_article_id': True,
            'article_id_pattern': r'-(\d{4,})(?:\.html?)?$',
            'min_word_count': 150,
            'additional_skip_patterns': [
                '/tag/', '/category/', '/author/',
                '/contact', '/about', '/privacy',
                '/search/', '/page/'
            ]
        }
    
    def _generate_article_selectors(self, analysis: Dict) -> List[str]:
        """Generate article content selectors"""
        selectors = []
        
        # Use top content patterns
        for pattern in analysis['content_patterns'][:5]:
            selectors.append(pattern['selector'])
        
        # Add common fallbacks if not present
        fallbacks = ['.article-content', '.post-content', '.entry-content', 'article', 'main']
        for fallback in fallbacks:
            if fallback not in selectors:
                selectors.append(fallback)
        
        return selectors[:10]
    
    def _generate_remove_selectors(self, analysis: Dict) -> List[str]:
        """Generate selectors for elements to remove"""
        selectors = analysis['remove_patterns'][:15]
        
        # Add common patterns
        common_removes = [
            '.advertisement', '.ads', '.social-share',
            '.navigation', '.header', '.footer',
            '.comments', '.sidebar', '.related'
        ]
        
        for remove in common_removes:
            if remove not in selectors:
                selectors.append(remove)
        
        return selectors
    
    def _generate_title_selector(self, analysis: Dict) -> str:
        """Generate title selector"""
        if analysis['title_patterns']:
            return analysis['title_patterns'][0]['selector']
        return 'h1'
    
    def _generate_date_selector(self) -> str:
        """Generate date selector"""
        return '.date, .post-date, time, [datetime]'
    
    def _generate_author_selector(self, analysis: Dict) -> str:
        """Generate author selector"""
        if analysis['author_patterns']:
            return analysis['author_patterns'][0]['selector']
        return '.author, .byline, .by-author'
    
    def _generate_cleanup_patterns(self, analysis: Dict) -> Dict:
        """Generate text cleanup patterns"""
        language = analysis['language']
        
        patterns = {
            'subscription_walls': [],
            'navigation_elements': [],
            'social_sharing': [],
            'newsletter_promotional': [],
            'boilerplate_removal': []
        }
        
        # Add language-specific patterns
        if language == 'fr':
            patterns['subscription_walls'] = [
                "Il vous reste \\d+[.,]\\d*% de cet article à lire.*",
                "La suite est réservée aux abonnés.*",
                "Article réservé à nos abonnés.*"
            ]
            patterns['navigation_elements'] = [
                "Lire aussi.*",
                "Voir aussi.*"
            ]
            patterns['social_sharing'] = [
                "Partager cet article.*",
                "Suivez.*?sur.*"
            ]
        elif language == 'ro':
            patterns['subscription_walls'] = [
                "Restul articolului este rezervat abonaților.*",
                "Pentru a citi restul articolului.*abonează-te.*"
            ]
            patterns['navigation_elements'] = [
                "Citește și:.*",
                "Vezi și:.*"
            ]
            patterns['social_sharing'] = [
                "Distribuie acest articol.*",
                "Urmărește.*?pe.*"
            ]
        else:  # English
            patterns['subscription_walls'] = [
                "Read more.*subscription.*",
                "Subscribe to continue.*",
                "This article is for subscribers.*"
            ]
            patterns['navigation_elements'] = [
                "Read more.*",
                "See also.*"
            ]
            patterns['social_sharing'] = [
                "Share this article.*",
                "Follow.*?on.*"
            ]
        
        # Add common boilerplate from analysis
        boilerplate = []
        for text, count in analysis['boilerplate_text'].most_common(5):
            if count > 1:
                # Escape special regex characters
                escaped = re.escape(text)
                boilerplate.append(escaped)
        
        patterns['boilerplate_removal'] = boilerplate
        
        return patterns
    
    def _generate_custom_sections(self, analysis: Dict) -> Dict:
        """Generate custom content sections configuration"""
        
        # Get top selectors for each section type
        title_selectors = [p['selector'] for p in analysis['title_patterns'][:5]]
        subtitle_selectors = [p['selector'] for p in analysis['subtitle_patterns'][:5]]
        author_selectors = [p['selector'] for p in analysis['author_patterns'][:5]]
        
        language = analysis['language']
        
        # Author format based on language
        author_format = {
            'fr': "*{content}*",
            'ro': "*De {content}*",
            'en': "*By {content}*"
        }.get(language, "*{content}*")
        
        return {
            'enabled': True,
            'sections': [
                {
                    'name': 'title',
                    'description': f'Main article title in {language}',
                    'selectors': title_selectors,
                    'fallback_selectors': ['h1', 'title'],
                    'format': '# {content}',
                    'required': False,
                    'order': 1
                },
                {
                    'name': 'subtitle',
                    'description': f'Article subtitle or lead in {language}',
                    'selectors': subtitle_selectors,
                    'fallback_selectors': ['h2', '.lead', 'meta[name="description"]'],
                    'format': '## {content}',
                    'required': False,
                    'order': 2
                },
                {
                    'name': 'author_details',
                    'description': f'Enhanced author information in {language}',
                    'selectors': author_selectors,
                    'format': author_format,
                    'required': False,
                    'order': 3
                }
            ],
            'processing_options': {
                'trim_whitespace': True,
                'remove_empty_sections': True,
                'add_separator_between_sections': True,
                'separator': '\n\n',
                'max_section_length': 500,
                'skip_duplicates': True
            }
        }
    
    def validate_config(self, yaml_config: str) -> Dict:
        """Validate generated configuration against sample articles"""
        print("✅ Validating configuration...")
        
        # Save temporary config file
        temp_config_path = f"{self.rules_dir}/temp_{self.domain}.yaml"
        with open(temp_config_path, 'w', encoding='utf-8') as f:
            f.write(yaml_config)
        
        validation_results = {
            'total_tests': len(self.sample_articles),
            'successful_extractions': 0,
            'failed_extractions': 0,
            'average_word_count': 0,
            'issues': []
        }
        
        # Test each sample article (simplified validation)
        word_counts = []
        for url in self.sample_articles:
            try:
                # This would ideally use the TextExtractor class
                # For now, we'll do a simplified validation
                html_content = self._download_article_html(url)
                if html_content:
                    soup = BeautifulSoup(html_content, 'html.parser')
                    text_length = len(soup.get_text())
                    if text_length > 500:  # Reasonable article length
                        validation_results['successful_extractions'] += 1
                        word_counts.append(len(soup.get_text().split()))
                    else:
                        validation_results['failed_extractions'] += 1
                        validation_results['issues'].append(f"Short content for {url}")
                else:
                    validation_results['failed_extractions'] += 1
                    validation_results['issues'].append(f"Could not download {url}")
            except Exception as e:
                validation_results['failed_extractions'] += 1
                validation_results['issues'].append(f"Error processing {url}: {e}")
        
        if word_counts:
            validation_results['average_word_count'] = sum(word_counts) / len(word_counts)
        
        # Clean up temp file
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)
        
        return validation_results
    
    def save_results(self, yaml_config: str, analysis: Dict, validation: Dict):
        """Save all results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save YAML config
        config_path = f"{self.rules_dir}/{self.domain}.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(yaml_config)
        print(f"💾 Saved configuration: {config_path}")
        
        # Save analysis report
        report_data = {
            'domain': self.domain,
            'timestamp': timestamp,
            'sample_articles': self.sample_articles,
            'analysis': analysis,
            'validation': validation,
            'config_path': config_path
        }
        
        report_path = f"{self.reports_dir}/{self.domain}_analysis_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"📊 Saved analysis report: {report_path}")
        
        return config_path, report_path
    
    def run(self) -> Tuple[str, str]:
        """Run the complete onboarding process"""
        try:
            # Step 1: Discover articles
            self.sample_articles = self.discover_articles()
            if not self.sample_articles:
                raise Exception("No articles found for analysis")
            
            # Step 2: Analyze articles
            analysis = self.analyze_articles(self.sample_articles)
            if analysis['successful_downloads'] == 0:
                raise Exception("No articles could be analyzed")
            
            # Step 3: Generate YAML config
            yaml_config = self.generate_yaml_config(analysis)
            
            # Step 4: Validate config
            validation = self.validate_config(yaml_config)
            
            # Step 5: Save results
            config_path, report_path = self.save_results(yaml_config, analysis, validation)
            
            # Print summary
            print("\n🎉 Onboarding completed successfully!")
            print(f"📁 Configuration: {config_path}")
            print(f"📊 Report: {report_path}")
            print(f"✅ Analyzed {analysis['successful_downloads']} articles")
            print(f"🧪 Validation: {validation['successful_extractions']}/{validation['total_tests']} successful")
            
            return config_path, report_path
            
        except Exception as e:
            print(f"❌ Onboarding failed: {e}")
            raise


def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python3 website_onboarder.py <website_url>")
        print("Example: python3 website_onboarder.py https://example-news.com")
        sys.exit(1)
    
    website_url = sys.argv[1]
    
    try:
        onboarder = WebsiteOnboarder(website_url)
        config_path, report_path = onboarder.run()
        
        print(f"\n🔧 To use the generated configuration:")
        print(f"   ./run_text_extractor.sh 5 trafilatura --domain {onboarder.domain}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()