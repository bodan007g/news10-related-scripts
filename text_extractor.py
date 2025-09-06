#!/usr/bin/env python3
"""
Text Extractor Script
Extracts clean article text from HTML files using generic and website-specific rules.
"""

import os
import json
import yaml
import html2text
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from readability import Document
import re
from text_cleanup import MultiLanguageTextCleaner

# Configuration
CONTENT_DIR = "content"
EXTRACTION_RULES_DIR = "extraction_rules"
LOGS_DIR = "logs"
STATUS_FILE = "text_extractor_status.json"

class TextExtractor:
    def __init__(self):
        self.processed_status = self.load_status()
        self.text_cleaner = MultiLanguageTextCleaner()
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'already_processed': 0,
            'skipped_files': 0,
            'cleaned_by_language': {}
        }
        # Configure html2text
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # Don't wrap lines

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

    def load_extraction_rules(self, domain):
        """Load website-specific extraction rules"""
        rules_file = os.path.join(EXTRACTION_RULES_DIR, f"{domain}.yaml")
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Error loading rules for {domain}: {e}")
        return None

    def should_skip_file(self, file_path, rules):
        """Check if file should be skipped based on URL patterns"""
        if not rules or 'skip_urls_containing' not in rules:
            return False
        
        for pattern in rules['skip_urls_containing']:
            if pattern in file_path:
                return True
        return False

    def clean_html_generic(self, html_content):
        """Generic HTML cleaning using readability and BeautifulSoup"""
        try:
            # Use readability to extract main content
            doc = Document(html_content)
            clean_html = doc.content()
            
            # Further cleaning with BeautifulSoup
            soup = BeautifulSoup(clean_html, 'html.parser')
            
            # Remove unwanted elements
            unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 
                           'aside', 'iframe', 'form', 'button']
            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove elements with unwanted classes/ids
            unwanted_patterns = ['ad', 'advertisement', 'promo', 'social', 'share',
                               'related', 'sidebar', 'navigation', 'comment']
            for element in soup.find_all():
                if element.get('class'):
                    classes = ' '.join(element.get('class', []))
                    if any(pattern in classes.lower() for pattern in unwanted_patterns):
                        element.decompose()
                        continue
                if element.get('id'):
                    element_id = element.get('id', '').lower()
                    if any(pattern in element_id for pattern in unwanted_patterns):
                        element.decompose()
            
            return str(soup)
        
        except Exception as e:
            print(f"Error in generic cleaning: {e}")
            return html_content

    def extract_with_rules(self, soup, rules):
        """Extract content using website-specific rules"""
        if not rules:
            return None
        
        # Remove unwanted elements first
        if 'remove_selectors' in rules:
            for selector in rules['remove_selectors']:
                for element in soup.select(selector):
                    element.decompose()
        
        # Try to find article content
        article_content = None
        if 'article_selectors' in rules:
            for selector in rules['article_selectors']:
                elements = soup.select(selector)
                if elements:
                    # If multiple elements found, combine them
                    if len(elements) > 1:
                        combined = soup.new_tag('div')
                        for elem in elements:
                            combined.append(elem)
                        article_content = combined
                    else:
                        article_content = elements[0]
                    break
        
        return article_content

    def extract_metadata(self, soup, rules, original_url=""):
        """Extract metadata from the page"""
        metadata = {
            'title': '',
            'author': '',
            'date': '',
            'url': original_url
        }
        
        if not rules:
            # Generic extraction
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()
            
            # Try common meta tags
            for tag in soup.find_all('meta'):
                if tag.get('name') == 'author':
                    metadata['author'] = tag.get('content', '')
                elif tag.get('property') == 'article:author':
                    metadata['author'] = tag.get('content', '')
                elif tag.get('name') == 'date':
                    metadata['date'] = tag.get('content', '')
                elif tag.get('property') == 'article:published_time':
                    metadata['date'] = tag.get('content', '')
        else:
            # Use website-specific selectors
            if 'title_selector' in rules:
                title_elem = soup.select_one(rules['title_selector'])
                if title_elem:
                    metadata['title'] = title_elem.get_text().strip()
            
            if 'author_selector' in rules:
                author_elem = soup.select_one(rules['author_selector'])
                if author_elem:
                    metadata['author'] = author_elem.get_text().strip()
            
            if 'date_selector' in rules:
                date_elem = soup.select_one(rules['date_selector'])
                if date_elem:
                    metadata['date'] = date_elem.get_text().strip()
        
        return metadata

    def html_to_markdown(self, html_content, domain=""):
        """Convert HTML to clean Markdown with language-specific cleanup"""
        try:
            markdown = self.html_converter.handle(html_content)
            
            # Apply language-specific text cleaning
            cleaned_markdown = self.text_cleaner.clean_text(markdown, domain=domain)
            
            # Track cleaning statistics
            language = self.text_cleaner.detect_language(markdown, domain)
            if language not in self.stats['cleaned_by_language']:
                self.stats['cleaned_by_language'][language] = 0
            self.stats['cleaned_by_language'][language] += 1
            
            return cleaned_markdown
        except Exception as e:
            print(f"Error converting to markdown: {e}")
            return html_content

    def reconstruct_url(self, domain, file_path):
        """Reconstruct original URL from file path"""
        # Extract path from filename
        filename = os.path.basename(file_path)
        if filename == 'index.html':
            return f"https://{domain}/"
        
        # Remove .html extension and convert underscores back to slashes
        url_path = filename.replace('.html', '').replace('_', '/')
        return f"https://{domain}/{url_path}"

    def process_html_file(self, file_path, domain):
        """Process a single HTML file"""
        # Check if already processed
        file_key = f"{domain}:{file_path}"
        if file_key in self.processed_status and self.processed_status[file_key]['status'] == 'success':
            self.stats['already_processed'] += 1
            return
        
        # Load extraction rules for domain
        rules = self.load_extraction_rules(domain)
        
        # Check if file should be skipped
        if self.should_skip_file(file_path, rules):
            self.stats['skipped_files'] += 1
            self.processed_status[file_key] = {
                'status': 'skipped',
                'reason': 'URL pattern match',
                'processed_at': datetime.now().isoformat()
            }
            return
        
        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Reconstruct original URL
            original_url = self.reconstruct_url(domain, file_path)
            
            # Extract metadata
            metadata = self.extract_metadata(soup, rules, original_url)
            
            # Try website-specific extraction first
            article_content = self.extract_with_rules(soup, rules)
            
            if not article_content:
                # Fall back to generic extraction
                clean_html = self.clean_html_generic(html_content)
                soup = BeautifulSoup(clean_html, 'html.parser')
                article_content = soup
            
            if article_content:
                # Convert to markdown with domain-specific cleanup
                article_html = str(article_content)
                markdown_content = self.html_to_markdown(article_html, domain)
                
                # Skip if content is too short (likely not a real article)
                if len(markdown_content.strip()) < 100:
                    self.stats['skipped_files'] += 1
                    self.processed_status[file_key] = {
                        'status': 'skipped',
                        'reason': 'Content too short',
                        'processed_at': datetime.now().isoformat()
                    }
                    return
                
                # Generate output paths
                rel_path = os.path.relpath(file_path, CONTENT_DIR)
                extracted_path = rel_path.replace('/raw/', '/extracted/').replace('.html', '.md')
                metadata_path = rel_path.replace('/raw/', '/metadata/').replace('.html', '.yaml')
                
                full_extracted_path = os.path.join(CONTENT_DIR, extracted_path)
                full_metadata_path = os.path.join(CONTENT_DIR, metadata_path)
                
                # Create output directories
                os.makedirs(os.path.dirname(full_extracted_path), exist_ok=True)
                os.makedirs(os.path.dirname(full_metadata_path), exist_ok=True)
                
                # Save markdown content
                with open(full_extracted_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                # Save initial metadata
                metadata.update({
                    'extracted_at': datetime.now().isoformat(),
                    'source_file': file_path,
                    'markdown_file': full_extracted_path,
                    'content_length': len(markdown_content),
                    'extraction_method': 'website_rules' if rules else 'generic'
                })
                
                with open(full_metadata_path, 'w', encoding='utf-8') as f:
                    yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
                
                # Update status
                self.processed_status[file_key] = {
                    'status': 'success',
                    'markdown_file': full_extracted_path,
                    'metadata_file': full_metadata_path,
                    'content_length': len(markdown_content),
                    'processed_at': datetime.now().isoformat()
                }
                
                self.stats['successful_extractions'] += 1
                print(f"✓ Extracted: {original_url} -> {full_extracted_path}")
            else:
                raise Exception("No article content found")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.stats['failed_extractions'] += 1
            
            self.processed_status[file_key] = {
                'status': 'error',
                'error': str(e),
                'processed_at': datetime.now().isoformat()
            }
        
        self.stats['total_processed'] += 1

    def find_html_files(self):
        """Find all HTML files to process"""
        html_files = []
        if not os.path.exists(CONTENT_DIR):
            return html_files
        
        for root, dirs, files in os.walk(CONTENT_DIR):
            if 'raw' in root:
                for file in files:
                    if file.endswith('.html'):
                        file_path = os.path.join(root, file)
                        # Extract domain from path
                        path_parts = root.split(os.sep)
                        domain = None
                        for i, part in enumerate(path_parts):
                            if part.startswith('www.') or part.count('.') >= 1:
                                domain = part
                                break
                        
                        if domain:
                            html_files.append((file_path, domain))
        
        return html_files

    def run(self):
        """Main processing function"""
        start_time = time.time()
        print(f"Text Extractor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Find all HTML files to process
        html_files = self.find_html_files()
        if not html_files:
            print("No HTML files found to process")
            return
        
        print(f"Found {len(html_files)} HTML files to process")
        
        # Process each file
        for file_path, domain in html_files:
            print(f"Processing: {file_path}")
            self.process_html_file(file_path, domain)
        
        # Save status and print summary
        self.save_status()
        
        elapsed = time.time() - start_time
        print(f"\n=== Text Extractor Summary ===")
        print(f"Total files processed: {self.stats['total_processed']}")
        print(f"Successful extractions: {self.stats['successful_extractions']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        print(f"Already processed: {self.stats['already_processed']}")
        print(f"Skipped files: {self.stats['skipped_files']}")
        
        # Show language cleaning statistics
        if self.stats['cleaned_by_language']:
            print("Language-specific cleaning:")
            for language, count in self.stats['cleaned_by_language'].items():
                print(f"  {language}: {count} files")
        
        print(f"Total time: {elapsed:.2f} seconds")
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "text_extractor_summary.log")
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Processed: {self.stats['total_processed']} | "
            f"Extracted: {self.stats['successful_extractions']} | "
            f"Failed: {self.stats['failed_extractions']} | "
            f"Skipped: {self.stats['skipped_files']} | "
            f"Time: {elapsed_time:.2f}s\n"
        )
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    import time
    extractor = TextExtractor()
    extractor.run()