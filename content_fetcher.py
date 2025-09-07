#!/usr/bin/env python3
"""
Content Fetcher Script
Fetches HTML content for discovered article URLs and saves them to organized directories.
"""

import os
import csv
import requests
import time
from datetime import datetime
from urllib.parse import urlparse, urljoin
import json
from content_filters import UniversalContentFilter

# Configuration
LOGS_DIR = "logs"
CONTENT_DIR = "content"
CACHE_DIR = "cache"
STATUS_FILE = "content_fetcher_status.json"
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1  # Delay between requests to be respectful

class ContentFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.processed_status = self.load_status()
        self.content_filter = UniversalContentFilter()
        self.stats = {
            'total_processed': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'already_processed': 0,
            'filtered_urls': 0
        }

    def load_status(self):
        """Load processing status from file to avoid re-downloading"""
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

    def extract_article_id_from_url(self, url):
        """Extract article ID from URL using the same patterns as content filter"""
        import re
        
        # Article ID patterns - same as in content_filters.py
        patterns = [
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
            r'/(\d{6,})$'               # Ends with 6+ digits after slash
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_content_path(self, domain, url_path, month_str, full_url=None):
        """Generate file path for content storage using original URL structure"""
        # Clean the URL path
        clean_path = url_path.strip('/')
        
        # Skip empty, root, or invalid paths
        invalid_paths = ['', '/', '?getmobile=1', '--><!--', '-->', '<!--', '<!', '--']
        if not clean_path or clean_path in invalid_paths or clean_path.startswith('-->') or clean_path.startswith('<!--'):
            return None  # Signal to skip this URL
        
        # Extract the last meaningful part of the path for filename
        if '/' in clean_path:
            # Get the last part of the path (usually the article slug)
            parts = clean_path.split('/')
            filename_part = parts[-1]
        else:
            filename_part = clean_path
        
        # Clean up the filename part
        safe_filename = filename_part.replace('?', '_').replace('#', '_').replace('&', '_')
        
        # Remove query parameters if they exist
        if '?' in safe_filename:
            safe_filename = safe_filename.split('?')[0]
        
        # Ensure it's not empty after cleaning
        if not safe_filename or safe_filename.isdigit():
            # If only digits or empty, use a fallback based on article ID
            article_id = self.extract_article_id_from_url(full_url) if full_url else None
            if article_id:
                safe_filename = f"article_{article_id}"
            else:
                # Last resort: use a hash of the path
                import hashlib
                safe_filename = hashlib.md5(url_path.encode()).hexdigest()[:10]
        
        # Ensure filename ends with .html
        if not safe_filename.endswith('.html'):
            safe_filename += '.html'
        
        # Create directory structure
        content_dir = os.path.join(CONTENT_DIR, month_str, domain, 'raw')
        os.makedirs(content_dir, exist_ok=True)
        
        return os.path.join(content_dir, safe_filename)

    def download_content(self, url):
        """Download HTML content from URL"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None

    def process_domain_links(self, domain, csv_file, limit=None):
        """Process all links for a specific domain with optional limit"""
        if not os.path.exists(csv_file):
            print(f"CSV file not found: {csv_file}")
            return

        month_str = os.path.basename(os.path.dirname(csv_file))
        domain_stats = {
            'processed': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0
        }

        successfully_saved_count = 0  # Count only successfully saved files
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                
                timestamp, url_path = row[0], row[1]
                full_url = f"https://{domain}{url_path}"
                
                # Check if already processed
                url_key = f"{month_str}:{domain}:{url_path}"
                if url_key in self.processed_status and self.processed_status[url_key]['status'] == 'success':
                    domain_stats['skipped'] += 1
                    self.stats['already_processed'] += 1
                    continue

                # Early path validation - check if this would generate a valid file path
                test_file_path = self.get_content_path(domain, url_path, month_str, full_url)
                if not test_file_path:
                    # Skip invalid URLs (empty paths, root pages, etc.) early
                    domain_stats['skipped'] += 1
                    self.stats['filtered_urls'] += 1
                    print(f"SKIPPED: {full_url} (invalid path)")
                    
                    # Update status to avoid reprocessing
                    self.processed_status[url_key] = {
                        'status': 'filtered',
                        'reason': 'invalid path',
                        'processed_at': datetime.now().isoformat()
                    }
                    continue

                # Apply content filtering before download
                domain_config = self.content_filter.load_domain_config(domain)
                should_skip, reason = self.content_filter.should_skip_url(full_url, domain_config)
                
                if should_skip:
                    domain_stats['skipped'] += 1
                    self.stats['filtered_urls'] += 1
                    print(f"FILTERED: {full_url} ({reason})")
                    
                    # Update status with filter reason
                    self.processed_status[url_key] = {
                        'status': 'filtered',
                        'reason': reason,
                        'processed_at': datetime.now().isoformat()
                    }
                    continue

                domain_stats['processed'] += 1
                self.stats['total_processed'] += 1
                
                print(f"Fetching: {full_url}")
                
                # Download content
                html_content = self.download_content(full_url)
                
                if html_content:
                    # Save to file (we already know the path is valid)
                    file_path = test_file_path
                    
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        # Update status
                        self.processed_status[url_key] = {
                            'status': 'success',
                            'file_path': file_path,
                            'processed_at': datetime.now().isoformat(),
                            'content_length': len(html_content)
                        }
                        
                        domain_stats['downloaded'] += 1
                        self.stats['successful_downloads'] += 1
                        successfully_saved_count += 1
                        print(f"✓ Saved to: {file_path}")
                        
                        # Check limit AFTER successful save
                        if limit and successfully_saved_count >= limit:
                            print(f"Reached limit of {limit} successfully saved files for domain {domain}")
                            break
                        
                    except Exception as e:
                        print(f"Error saving {file_path}: {e}")
                        domain_stats['failed'] += 1
                        self.stats['failed_downloads'] += 1
                        
                        # Update status with error
                        self.processed_status[url_key] = {
                            'status': 'error',
                            'error': str(e),
                            'processed_at': datetime.now().isoformat()
                        }
                else:
                    domain_stats['failed'] += 1
                    self.stats['failed_downloads'] += 1
                    
                    # Update status with error
                    self.processed_status[url_key] = {
                        'status': 'error',
                        'error': 'Failed to download content',
                        'processed_at': datetime.now().isoformat()
                    }

                # Be respectful - add delay between requests
                time.sleep(REQUEST_DELAY)

        print(f"Domain {domain} stats: {domain_stats}")

    def find_csv_files(self):
        """Find all CSV files in logs directory"""
        csv_files = []
        if not os.path.exists(LOGS_DIR):
            return csv_files
        
        for month_dir in os.listdir(LOGS_DIR):
            month_path = os.path.join(LOGS_DIR, month_dir)
            if not os.path.isdir(month_path):
                continue
            
            for file in os.listdir(month_path):
                if file.endswith('.csv') and not file.startswith('summary'):
                    domain = file.replace('.csv', '')
                    csv_path = os.path.join(month_path, file)
                    csv_files.append((domain, csv_path))
        
        return csv_files

    def run(self, limit=None):
        """Main processing function with optional limit per domain"""
        start_time = time.time()
        print(f"Content Fetcher started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if limit:
            print(f"Processing limit: {limit} URLs per domain")
        
        # Find all CSV files to process
        csv_files = self.find_csv_files()
        if not csv_files:
            print("No CSV files found to process")
            return
        
        print(f"Found {len(csv_files)} domain CSV files to process")
        
        # Process each domain
        for domain, csv_file in csv_files:
            print(f"\nProcessing domain: {domain}")
            self.process_domain_links(domain, csv_file, limit)
            
        # Save status and print summary
        self.save_status()
        
        elapsed = time.time() - start_time
        print(f"\n=== Content Fetcher Summary ===")
        print(f"Total URLs processed: {self.stats['total_processed']}")
        print(f"Successful downloads: {self.stats['successful_downloads']}")
        print(f"Failed downloads: {self.stats['failed_downloads']}")
        print(f"Already processed: {self.stats['already_processed']}")
        print(f"Filtered URLs (skipped): {self.stats['filtered_urls']}")
        print(f"Total time: {elapsed:.2f} seconds")
        
        # Write summary to log
        self.write_summary_log(elapsed)

    def write_summary_log(self, elapsed_time):
        """Write processing summary to log file"""
        now = datetime.now()
        month_str = now.strftime("%Y-%m")
        month_dir = os.path.join(LOGS_DIR, month_str)
        os.makedirs(month_dir, exist_ok=True)
        
        summary_log_path = os.path.join(month_dir, "content_fetcher_summary.log")
        
        log_entry = (
            f"{now.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Processed: {self.stats['total_processed']} | "
            f"Downloaded: {self.stats['successful_downloads']} | "
            f"Failed: {self.stats['failed_downloads']} | "
            f"Skipped: {self.stats['already_processed']} | "
            f"Time: {elapsed_time:.2f}s\n"
        )
        
        with open(summary_log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

if __name__ == "__main__":
    import sys
    
    # Check for limit argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            if limit <= 0:
                print("Error: Limit must be a positive integer")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid limit value. Must be an integer.")
            sys.exit(1)
    
    fetcher = ContentFetcher()
    fetcher.run(limit)