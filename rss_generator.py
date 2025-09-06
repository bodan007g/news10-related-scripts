#!/usr/bin/env python3
"""
RSS Generator Script
Generates RSS feeds for processed news articles with importance filtering and categorization.
"""

import os
import yaml
import json
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import time

# Configuration
CONTENT_DIR = "content"
RSS_DIR = "rss"
LOGS_DIR = "logs"
STATUS_FILE = "rss_generator_status.json"
MAX_ARTICLES_PER_FEED = 10
IMPORTANCE_THRESHOLD = 0.4  # Minimum importance score for inclusion

class RSSGenerator:
    def __init__(self):
        self.processed_status = self.load_status()
        self.stats = {
            'feeds_generated': 0,
            'articles_processed': 0,
            'articles_included': 0,
            'articles_filtered': 0
        }
        # Ensure RSS directory exists
        os.makedirs(RSS_DIR, exist_ok=True)

    def load_status(self):
        """Load processing status from file"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_status(self):
        """Save processing status to file"""
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.processed_status, f, indent=2)

    def load_article_metadata(self, metadata_file):
        """Load article metadata from YAML file"""
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading metadata from {metadata_file}: {e}")
            return None

    def create_rss_element(self, title, link, description):
        """Create the root RSS element with channel information"""
        rss = Element('rss')
        rss.set('version', '2.0')
        rss.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
        rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
        
        channel = SubElement(rss, 'channel')
        
        # Channel metadata
        SubElement(channel, 'title').text = title
        SubElement(channel, 'link').text = link
        SubElement(channel, 'description').text = description
        SubElement(channel, 'language').text = 'ro'  # Romanian for Romanian sites
        SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        SubElement(channel, 'generator').text = 'News Processing Pipeline'
        
        # Self-referencing link
        atom_link = SubElement(channel, 'atom:link')
        atom_link.set('href', f'{link}/rss.xml')
        atom_link.set('rel', 'self')
        atom_link.set('type', 'application/rss+xml')
        
        return rss, channel

    def add_article_to_rss(self, channel, metadata):
        """Add an article item to the RSS channel"""
        item = SubElement(channel, 'item')
        
        # Required elements
        SubElement(item, 'title').text = metadata.get('title', 'Untitled')
        SubElement(item, 'link').text = metadata.get('url', '')
        SubElement(item, 'guid').text = metadata.get('url', '')
        
        # Description (use summary if available, otherwise truncate content)
        description = metadata.get('summary', '')
        if not description and 'content_length' in metadata:
            description = f"Article with {metadata['content_length']} words"
        SubElement(item, 'description').text = description
        
        # Publication date
        pub_date = self.format_pub_date(metadata.get('date', ''))
        if pub_date:
            SubElement(item, 'pubDate').text = pub_date
        
        # Author
        author = metadata.get('author', '')
        if author:
            SubElement(item, 'dc:creator').text = author
        
        # Categories
        categories = metadata.get('categories', [])
        for category in categories:
            SubElement(item, 'category').text = category
        
        # Custom elements for additional metadata
        if 'importance_score' in metadata:
            SubElement(item, 'importance').text = str(metadata['importance_score'])
        
        if 'sentiment' in metadata:
            SubElement(item, 'sentiment').text = metadata['sentiment']

    def format_pub_date(self, date_str):
        """Format publication date for RSS (RFC 822 format)"""
        if not date_str:
            return datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # Try to parse various date formats
        date_patterns = [
            '%Y-%m-%dT%H:%M:%S.%f',  # ISO format with microseconds
            '%Y-%m-%dT%H:%M:%S',     # ISO format
            '%Y-%m-%d %H:%M:%S',     # Standard format
            '%Y-%m-%d',              # Date only
        ]
        
        for pattern in date_patterns:
            try:
                dt = datetime.strptime(date_str, pattern)
                return dt.strftime('%a, %d %b %Y %H:%M:%S %z')
            except ValueError:
                continue
        
        # If all parsing fails, return current time
        return datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

    def prettify_xml(self, elem):
        """Return a pretty-printed XML string"""
        rough_string = tostring(elem, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ").replace('<?xml version="1.0" ?>\n', '<?xml version="1.0" encoding="UTF-8"?>\n')

    def collect_articles_for_website(self, domain):
        """Collect all articles for a specific website"""
        articles = []
        
        if not os.path.exists(CONTENT_DIR):
            return articles
        
        # Look through all month directories
        for month_dir in os.listdir(CONTENT_DIR):
            month_path = os.path.join(CONTENT_DIR, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            # Check if this domain exists in this month
            domain_path = os.path.join(month_path, domain)
            if not os.path.exists(domain_path):
                continue
            
            # Look for metadata files
            metadata_path = os.path.join(domain_path, 'metadata')
            if not os.path.exists(metadata_path):
                continue
            
            for filename in os.listdir(metadata_path):
                if filename.endswith('.yaml'):
                    metadata_file = os.path.join(metadata_path, filename)
                    metadata = self.load_article_metadata(metadata_file)
                    
                    if metadata:
                        # Add month info for sorting
                        metadata['_month'] = month_dir
                        metadata['_metadata_file'] = metadata_file
                        articles.append(metadata)
                        self.stats['articles_processed'] += 1
        
        return articles

    def filter_and_sort_articles(self, articles, category_filter=None):
        """Filter articles by importance and category, then sort by date"""
        filtered = []
        
        for article in articles:
            # Filter by importance score
            importance = article.get('importance_score', 0)
            if importance < IMPORTANCE_THRESHOLD:
                self.stats['articles_filtered'] += 1
                continue
            
            # Filter by category if specified
            if category_filter:
                categories = article.get('categories', [])
                if category_filter not in categories:
                    continue
            
            filtered.append(article)
            self.stats['articles_included'] += 1
        
        # Sort by importance score (descending) and then by date (newest first)
        filtered.sort(key=lambda x: (
            -x.get('importance_score', 0),
            x.get('ai_processed_at', x.get('extracted_at', ''))
        ), reverse=True)
        
        return filtered[:MAX_ARTICLES_PER_FEED]

    def generate_website_feed(self, domain):
        """Generate RSS feed for a specific website"""
        print(f"Generating RSS feed for {domain}")
        
        # Collect articles
        articles = self.collect_articles_for_website(domain)
        if not articles:
            print(f"No articles found for {domain}")
            return
        
        # Filter and sort articles
        filtered_articles = self.filter_and_sort_articles(articles)
        if not filtered_articles:
            print(f"No articles meet the criteria for {domain}")
            return
        
        # Create RSS feed
        feed_title = f"News from {domain}"
        feed_link = f"https://{domain}"
        feed_description = f"Latest news articles from {domain} (filtered by importance)"
        
        rss, channel = self.create_rss_element(feed_title, feed_link, feed_description)
        
        # Add articles to feed
        for article in filtered_articles:
            self.add_article_to_rss(channel, article)
        
        # Save RSS file
        rss_file = os.path.join(RSS_DIR, f"{domain}.xml")
        try:
            with open(rss_file, 'w', encoding='utf-8') as f:
                f.write(self.prettify_xml(rss))
            
            print(f"✓ Generated RSS feed: {rss_file} ({len(filtered_articles)} articles)")
            self.stats['feeds_generated'] += 1
            
            # Update status
            self.processed_status[f"rss:{domain}"] = {
                'status': 'generated',
                'file_path': rss_file,
                'article_count': len(filtered_articles),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error saving RSS file {rss_file}: {e}")

    def generate_category_feeds(self):
        """Generate category-based RSS feeds"""
        categories = ['politic', 'economic', 'social', 'international', 'health', 'technology', 'culture']
        
        for category in categories:
            print(f"Generating category feed for: {category}")
            
            # Collect articles from all websites for this category
            all_articles = []
            
            if not os.path.exists(CONTENT_DIR):
                continue
            
            for month_dir in os.listdir(CONTENT_DIR):
                month_path = os.path.join(CONTENT_DIR, month_dir)
                if not os.path.isdir(month_path):
                    continue
                
                # Look through all domains in this month
                for domain_dir in os.listdir(month_path):
                    domain_path = os.path.join(month_path, domain_dir)
                    if not os.path.isdir(domain_path):
                        continue
                    
                    metadata_path = os.path.join(domain_path, 'metadata')
                    if not os.path.exists(metadata_path):
                        continue
                    
                    for filename in os.listdir(metadata_path):
                        if filename.endswith('.yaml'):
                            metadata_file = os.path.join(metadata_path, filename)
                            metadata = self.load_article_metadata(metadata_file)
                            
                            if metadata:
                                metadata['_month'] = month_dir
                                metadata['_domain'] = domain_dir
                                all_articles.append(metadata)
            
            # Filter by category and importance
            filtered_articles = self.filter_and_sort_articles(all_articles, category)
            
            if not filtered_articles:
                print(f"No articles found for category: {category}")
                continue
            
            # Create RSS feed
            feed_title = f"News Category: {category.title()}"
            feed_link = "https://news.local"  # Placeholder
            feed_description = f"Latest news articles in category: {category}"
            
            rss, channel = self.create_rss_element(feed_title, feed_link, feed_description)
            
            # Add articles to feed
            for article in filtered_articles:
                self.add_article_to_rss(channel, article)
            
            # Save RSS file
            rss_file = os.path.join(RSS_DIR, f"category_{category}.xml")
            try:
                with open(rss_file, 'w', encoding='utf-8') as f:
                    f.write(self.prettify_xml(rss))
                
                print(f"✓ Generated category feed: {rss_file} ({len(filtered_articles)} articles)")
                self.stats['feeds_generated'] += 1
                
                # Update status
                self.processed_status[f"category:{category}"] = {
                    'status': 'generated',
                    'file_path': rss_file,
                    'article_count': len(filtered_articles),
                    'generated_at': datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"Error saving category RSS file {rss_file}: {e}")

    def find_websites(self):
        """Find all websites that have content"""
        websites = set()
        
        if not os.path.exists(CONTENT_DIR):
            return list(websites)
        
        for month_dir in os.listdir(CONTENT_DIR):
            month_path = os.path.join(CONTENT_DIR, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            for domain_dir in os.listdir(month_path):
                domain_path = os.path.join(month_path, domain_dir)
                if os.path.isdir(domain_path):
                    websites.add(domain_dir)
        
        return list(websites)

    def run(self):
        """Main processing function"""
        start_time = time.time()
        print(f"RSS Generator started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all websites
        websites = self.find_websites()
        if not websites:
            print("No websites found with content")
            return
        
        print(f"Found {len(websites)} websites with content: {', '.join(websites)}")
        
        # Generate individual website feeds
        for website in websites:
            self.generate_website_feed(website)
        
        # Generate category feeds
        self.generate_category_feeds()
        
        # Save status
        self.save_status()
        
        elapsed = time.time() - start_time
        
        print(f"\n=== RSS Generator Summary ===")
        print(f"Feeds generated: {self.stats['feeds_generated']}")
        print(f"Articles processed: {self.stats['articles_processed']}")
        print(f"Articles included: {self.stats['articles_included']}")
        print(f"Articles filtered: {self.stats['articles_filtered']}")
        print(f"Total time: {elapsed:.2f} seconds")
        
        # List generated feeds
        if os.path.exists(RSS_DIR):
            feeds = [f for f in os.listdir(RSS_DIR) if f.endswith('.xml')]
            print(f"\nGenerated RSS files in {RSS_DIR}/:")
            for feed in feeds:
                print(f"  - {feed}")
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "rss_generator_summary.log")
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Feeds: {self.stats['feeds_generated']} | "
            f"Processed: {self.stats['articles_processed']} | "
            f"Included: {self.stats['articles_included']} | "
            f"Filtered: {self.stats['articles_filtered']} | "
            f"Time: {elapsed_time:.2f}s\n"
        )
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    generator = RSSGenerator()
    generator.run()