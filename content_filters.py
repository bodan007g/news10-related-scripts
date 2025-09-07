#!/usr/bin/env python3
"""
Content Filtering System
Universal filtering for news content across multiple websites and languages.
"""

import re
import yaml
import os
from urllib.parse import urlparse, unquote

# Configuration
EXTRACTION_RULES_DIR = "extraction_rules"

class UniversalContentFilter:
    def __init__(self):
        # Universal skip patterns for all websites
        self.universal_skip_patterns = {
            'common': [
                # Shopping/Commerce
                '/shop', '/store', '/buy', '/product', '/cart', '/purchase',
                '/guide', '/test', '/review', '/comparison', '/best-',
                
                # Navigation/System pages
                '/faq', '/help', '/about', '/contact', '/legal', '/terms',
                '/privacy', '/sitemap', '/search', '/404', '/error',
                '/login', '/register', '/account', '/profile', '/dashboard',
                
                # Media/Technical
                '/rss', '/feed', '/xml', '/api/', '/embed/', '/iframe',
                '/widget/', '/app/', '/mobile/', '/newsletter/', '/podcast',
                
                # Advertising/Tracking URLs
                '?utm_', '?ref=', '?source=', '?campaign=', '?fbclid=',
                '?origin=', '?lmd_', '?tracking=', '?affiliate=', '#',
                
                # Archives/Categories (without article IDs)
                '/archive', '/category', '/categories', '/tag/', '/tags/',
                '/author/', '/date/', '/year/', '/month/', '/section/',
                
                # Social/External
                '/social', '/share', '/print', '/pdf', '/download'
            ],
            
            'french': [
                '/guides-d-achat/', '/guide-achat/', '/comparatif/',
                '/boutique/', '/abonnement/', '/subscription/',
                '/mentions-legales/', '/politique-confidentialite/',
                '/cgu/', '/conditions-utilisation/',
                '/services/', '/partenaires/', '/publicite/',
                '/applications-groupe/', '/annonces-legales/'
            ],
            
            'romanian': [
                '/ghid-', '/ghiduri/', '/test-', '/recenzie-', '/review-',
                '/anunturi/', '/reclame/', '/publicitate/',
                '/contact', '/despre-noi', '/despre/',
                '/politica-', '/termeni-', '/conditii/',
                '/abonament/', '/newsletter/', '/servicii/'
            ],
            
            'english': [
                '/guides/', '/guide/', '/reviews/', '/deals/', '/offers/',
                '/shop/', '/store/', '/buy/', '/subscription/',
                '/about-us/', '/contact-us/', '/privacy-policy/',
                '/terms-of-service/', '/advertise/', '/jobs/'
            ]
        }
        
        # Article ID patterns for different websites
        self.article_id_patterns = [
            r'[-_](\d{6,})[_-]',        # Le Monde: _6632905_3232
            r'/(\d{6,})\.html',         # Generic: /123456.html
            r'/(\d{6,})/',              # Generic: /123456/
            r'/article/(\d+)/',         # /article/123456/
            r'/news/(\d+)',             # /news/123456
            r'/story/(\d+)',            # /story/123456
            r'-a(\d+)\.html',           # Romanian: -a123456.html
            r'/(\d+)-[a-z]',            # /123456-title-here
            r'article-(\d+)',           # article-123456
            r'/stire-(\d+)',            # Romanian: /stire-123456
            r'/articol-(\d+)',          # Romanian: /articol-123456
            r'[-/](\d{7,})$',           # Romanian: ends with 7+ digits (bzi.ro, digi24.ro)
            r'-(\d{6,})$',              # Ends with 6+ digits after hyphen
            r'/(\d{6,})$',              # Ends with 6+ digits after slash
            r'-(\d{5,})$',              # Ends with 5+ digits after hyphen (digi24.ro)
            r'/(\d{5,})$'               # Ends with 5+ digits after slash (digi24.ro)
        ]

    def detect_language_from_domain(self, domain):
        """Detect language from domain name"""
        if domain.endswith('.ro'):
            return 'romanian'
        elif domain.endswith('.fr'):
            return 'french'
        elif domain.endswith(('.com', '.org', '.net', '.uk', '.us')):
            return 'english'
        else:
            return 'common'

    def has_article_id(self, url):
        """Check if URL contains an article ID pattern"""
        for pattern in self.article_id_patterns:
            if re.search(pattern, url):
                return True
        return False

    def extract_article_id(self, url):
        """Extract article ID from URL if present"""
        for pattern in self.article_id_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def is_category_page(self, url_path):
        """Check if URL appears to be a category/section page"""
        # Remove query parameters and fragments
        clean_path = url_path.split('?')[0].split('#')[0]
        
        # Category page patterns
        category_patterns = [
            r'^/[a-z-]+/?$',           # /politics/, /economy/
            r'^/[a-z-]+\.html?$',      # politics.html, economy.htm
            r'^/section/[a-z-]+/?$',   # /section/politics/
            r'^/category/[a-z-]+/?$',  # /category/politics/
            r'^/tag/[a-z-]+/?$',       # /tag/politics/
        ]
        
        for pattern in category_patterns:
            if re.match(pattern, clean_path, re.IGNORECASE):
                return True
        return False

    def should_skip_url(self, url, domain_config=None):
        """Main filtering function - determines if URL should be skipped"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = unquote(parsed.path).lower()
            query = parsed.query.lower()
            full_url = f"{path}?{query}" if query else path
            
            # Detect language from domain
            language = self.detect_language_from_domain(domain)
            
            # Check universal skip patterns
            patterns_to_check = self.universal_skip_patterns['common'].copy()
            if language in self.universal_skip_patterns:
                patterns_to_check.extend(self.universal_skip_patterns[language])
            
            # Check against patterns
            for pattern in patterns_to_check:
                if pattern in full_url:
                    return True, f"matches skip pattern: {pattern}"
            
            # Check domain-specific skip patterns
            if domain_config and 'content_filters' in domain_config:
                filters = domain_config['content_filters']
                
                # Check additional skip patterns
                additional_patterns = filters.get('additional_skip_patterns', [])
                for pattern in additional_patterns:
                    if pattern in full_url:
                        return True, f"matches domain-specific pattern: {pattern}"
                
                # Check if article ID is required
                if filters.get('require_article_id', False):
                    if not self.has_article_id(url):
                        # But allow if it's explicitly marked as acceptable
                        if not filters.get('allow_no_id_pages', False):
                            return True, "no article ID found"
            
            # Check if it's a category page
            if self.is_category_page(path):
                return True, "appears to be category page"
            
            # File extensions to skip
            skip_extensions = ['.xml', '.rss', '.pdf', '.zip', '.doc', '.docx', 
                             '.xls', '.xlsx', '.ppt', '.pptx', '.json']
            for ext in skip_extensions:
                if path.endswith(ext):
                    return True, f"file extension {ext}"
            
            return False, "passed all filters"
            
        except Exception as e:
            return True, f"error parsing URL: {e}"

    def load_domain_config(self, domain):
        """Load domain-specific configuration"""
        config_file = os.path.join(EXTRACTION_RULES_DIR, f"{domain}.yaml")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load config for {domain}: {e}")
        return None

    def filter_url_list(self, urls, domain=None):
        """Filter a list of URLs, return (kept_urls, skipped_urls_with_reasons)"""
        kept = []
        skipped = []
        
        domain_config = None
        if domain:
            domain_config = self.load_domain_config(domain)
        
        for url in urls:
            should_skip, reason = self.should_skip_url(url, domain_config)
            if should_skip:
                skipped.append((url, reason))
            else:
                kept.append(url)
        
        return kept, skipped

    def get_filter_stats(self, skipped_urls_with_reasons):
        """Generate statistics about filtering"""
        reason_counts = {}
        for url, reason in skipped_urls_with_reasons:
            if reason not in reason_counts:
                reason_counts[reason] = 0
            reason_counts[reason] += 1
        
        return {
            'total_skipped': len(skipped_urls_with_reasons),
            'reason_breakdown': reason_counts
        }


class ContentTypeClassifier:
    """BART-based content type classification"""
    
    def __init__(self):
        self.content_types = [
            "news_article",       # Real news - KEEP
            "opinion_article",    # Editorials/opinions - KEEP  
            "shopping_guide",     # Product reviews - SKIP
            "category_page",      # Navigation pages - SKIP
            "faq_page",          # Help content - SKIP
            "legal_page",        # Terms/Privacy - SKIP
            "advertisement",     # Ads/Promotions - SKIP
            "about_page"         # About/Contact - SKIP
        ]

    def classify_content(self, text, url=""):
        """Classify content type using BART (placeholder - implement when needed)"""
        try:
            from transformers import pipeline
            
            # Create a prompt for classification
            prompt = f"This web content from URL {url} appears to be about: {text[:500]}"
            
            classifier = pipeline("zero-shot-classification", 
                                model="facebook/bart-large-mnli")
            result = classifier(prompt, self.content_types)
            
            return result['labels'][0], result['scores'][0]
        except Exception as e:
            print(f"Warning: Content classification failed: {e}")
            # Simple fallback classification
            text_lower = text.lower()
            if any(word in text_lower for word in ['guide', 'test', 'review', 'best', 'top']):
                return 'shopping_guide', 0.7
            elif any(word in text_lower for word in ['about', 'contact', 'terms', 'privacy']):
                return 'about_page', 0.8
            else:
                return 'news_article', 0.5

    def should_keep_content(self, content_type, confidence_threshold=0.6):
        """Determine if content should be kept based on classification"""
        keep_types = ['news_article', 'opinion_article']
        return content_type in keep_types


if __name__ == "__main__":
    # Test the filtering system
    filter_system = UniversalContentFilter()
    
    test_urls = [
        "https://www.lemonde.fr/idees/article/2025/08/21/title_6632905_3232.html",
        "https://www.lemonde.fr/guides-d-achat/article/2025/05/28/best-chargers.html",
        "https://www.lemonde.fr/economie.html",
        "https://www.bzi.ro/stire-important-news-123456",
        "https://www.bzi.ro/contact",
        "https://www.digi24.ro/stiri/actualitate/politics/article-567890.html",
        "https://www.digi24.ro/stiri/externe/ue/putin-este-un-pradator-ursula-von-der-leyen-mesaj-dur-de-la-granita-poloniei-cu-belarus-3393525",
        "https://www.bzi.ro/concurs-pentru-ocuparea-functiei-de-manager-la-opera-nationala-romana-din-iasi-pana-cand-pot-fi-depuse-proiectele-de-management-5334351"
    ]
    
    print("Testing URL filtering:")
    for url in test_urls:
        should_skip, reason = filter_system.should_skip_url(url)
        status = "SKIP" if should_skip else "KEEP"
        print(f"{status}: {url} ({reason})")