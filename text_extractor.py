#!/usr/bin/env python3
"""
Text Extractor Script
Extracts clean article text from HTML files using generic and website-specific rules.
"""

import os
import json
import yaml
from datetime import datetime


# Configuration
import trafilatura
from newspaper import Article
import time
CONTENT_DIR = "content"
LOGS_DIR = "logs"
STATUS_FILE = "text_extractor_status.json"

class TextExtractor:
    def __init__(self, extraction_method='newspaper', save_cleaned_html=False):
        """
        Initialize TextExtractor
        
        Args:
            extraction_method (str): 'newspaper' (default) or 'trafilatura'
            save_cleaned_html (bool): If True, save cleaned HTML next to original files
        """
        if extraction_method not in ['trafilatura', 'newspaper']:
            raise ValueError("extraction_method must be 'trafilatura' or 'newspaper'")
        
        self.extraction_method = extraction_method
        self.save_cleaned_html = save_cleaned_html
        self.processed_status = self.load_status()
        self.stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'already_processed': 0,
            'skipped_files': 0
        }  # Don't wrap lines  # Don't wrap lines  # Don't wrap lines

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

    def clean_html_for_extraction(self, html_content):
        """
        Clean HTML by removing non-content elements while preserving structure
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: Cleaned HTML with only content-relevant elements
        """
        try:
            import re
            from bs4 import BeautifulSoup, Comment
            
            # Remove HTML comments first
            html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove any remaining comments (BeautifulSoup parsing)
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Remove unwanted elements
            unwanted_tags = [
                'script', 'style', 'nav', 'header', 'footer', 'aside',
                'iframe', 'embed', 'object', 'applet', 'form',
                'button', 'input', 'textarea', 'select', 'option',
                'noscript', 'meta', 'link', 'title'
            ]
            
            for tag_name in unwanted_tags:
                for tag in soup.find_all(tag_name):
                    tag.decompose()
            
            # Remove elements with common non-content classes/ids
            unwanted_selectors = [
                '[class*="advertisement"]', '[class*="ad-"]', '[class*="ads"]',
                '[class*="sidebar"]', '[class*="widget"]', '[class*="menu"]',
                '[class*="nav"]', '[class*="header"]', '[class*="footer"]',
                '[class*="social"]', '[class*="share"]', '[class*="comment"]',
                '[id*="advertisement"]', '[id*="ad-"]', '[id*="ads"]',
                '[id*="sidebar"]', '[id*="widget"]', '[id*="menu"]',
                '[id*="nav"]', '[id*="header"]', '[id*="footer"]'
            ]
            
            for selector in unwanted_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # Remove inline styles and other unwanted attributes
            for element in soup.find_all():
                if element.name:
                    # Remove style attribute
                    if 'style' in element.attrs:
                        del element.attrs['style']
                    # Remove other unwanted attributes while keeping essential ones
                    attrs_to_keep = ['href', 'src', 'alt', 'title']
                    element.attrs = {k: v for k, v in element.attrs.items() if k in attrs_to_keep}
            
            # Remove empty elements (except br, hr, img)
            for element in soup.find_all():
                if element.name not in ['br', 'hr', 'img'] and not element.get_text(strip=True):
                    element.decompose()
            
            # Convert to string and clean up multiple consecutive empty lines
            cleaned_html = str(soup)
            
            # Remove multiple consecutive empty lines (keep at most 2 consecutive newlines)
            cleaned_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_html)
            
            # Remove excessive whitespace between tags while preserving content spacing
            cleaned_html = re.sub(r'>\s{3,}<', '>\n<', cleaned_html)
            
            # Remove leading spaces/tabs on each line (trim each line)
            cleaned_html = re.sub(r'^[ \t]+', '', cleaned_html, flags=re.MULTILINE)
            
            return cleaned_html
            
        except Exception as e:
            print(f"HTML cleaning failed: {e}")
            return html_content  # Return original if cleaning fails  # Return original if cleaning fails  # Return original if cleaning fails  # Return original if cleaning fails







    def extract_with_trafilatura(self, html_content, original_url=""):
        """Extract article content using trafilatura"""
        try:
            # Extract text content
            text = trafilatura.extract(html_content, 
                                     include_comments=False,
                                     include_tables=True,
                                     include_links=False,
                                     url=original_url)
            
            # For trafilatura, we need to manually add paragraph breaks
            if text:
                # Split by single newlines and process
                lines = text.split('\n')
                formatted_lines = []
                
                for line in lines:
                    stripped = line.strip()
                    if stripped:  # Non-empty line
                        formatted_lines.append(stripped)
                    elif formatted_lines and formatted_lines[-1]:  # Empty line after content
                        formatted_lines.append('')  # Keep as paragraph separator
                
                # Join lines and ensure proper paragraph spacing
                text = '\n'.join(formatted_lines)
                # Convert single newlines between content to double newlines
                import re
                text = re.sub(r'\n(?=\S)', '\n\n', text)
            
            # Extract metadata (without fast parameter)
            metadata = trafilatura.extract_metadata(html_content)
            
            return text, metadata
        except Exception as e:
            print(f"Trafilatura extraction failed for {original_url}: {e}")
            return None, None

    def extract_with_newspaper(self, html_content, original_url=""):
        """Extract article content using newspaper3k"""
        try:
            # Create Article object
            article = Article(original_url)
            article.set_html(html_content)
            article.parse()
            
            # Add empty lines between paragraphs
            text = article.text
            if text:
                # Split by double newlines (existing paragraph breaks)
                paragraphs = text.split('\n\n')
                # Join with double empty lines for better spacing
                text = '\n\n'.join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
            
            # Create metadata object similar to trafilatura
            class NewspaperMetadata:
                def __init__(self, article):
                    self.title = article.title
                    self.author = ', '.join(article.authors) if article.authors else None
                    self.date = article.publish_date.strftime('%Y-%m-%d') if article.publish_date else None
                    self.url = original_url
            
            metadata = NewspaperMetadata(article)
            
            return text, metadata
            
        except Exception as e:
            print(f"Newspaper3k extraction failed for {original_url}: {e}")
            return None, None

    def format_headers_markdown(self, text, html_content=""):
        """Format headers in text with proper Markdown syntax"""
        if not text:
            return text
            
        lines = text.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                formatted_lines.append(line)
                continue
                
            # Check if this looks like a header
            is_header = False
            header_level = 1
            
            # Heuristics for detecting headers:
            # 1. Short lines (typically under 80 chars)
            # 2. No ending punctuation (., !, ?)
            # 3. Followed by content or empty line
            # 4. Not starting with common content words
            
            if (len(stripped) < 80 and 
                len(stripped) > 5 and
                not stripped.endswith(('.', '!', '?', ':', ';', ',') ) and
                not stripped.startswith(('În ', 'De ', 'Cu ', 'Pentru ', 'Prin ', 'Astfel', 'Așa', 'Dar', 'Și')) and
                # Check if next non-empty line exists and looks like content
                self._next_line_looks_like_content(lines, i)):
                
                is_header = True
                
                # Determine header level based on context and formatting
                if i == 0 or (i < 3 and not any(formatted_lines[-3:])):  # First meaningful line
                    header_level = 1
                elif any(keyword in stripped.lower() for keyword in ['actualizare', 'știrea inițială', 'concluzia', 'background', 'ce s-a întâmplat']):
                    header_level = 2
                else:
                    header_level = 2  # Default secondary header
            
            if is_header:
                # Format as Markdown header
                formatted_lines.append(f"{'#' * header_level} {stripped}")
                # Add underline for emphasis if requested
                if header_level == 1:
                    formatted_lines.append("=" * len(stripped))
                elif header_level == 2:
                    formatted_lines.append("-" * len(stripped))
            else:
                formatted_lines.append(line)
                
        return '\n'.join(formatted_lines)
    
    def _next_line_looks_like_content(self, lines, current_index):
        """Check if the next non-empty line looks like content rather than another header"""
        for i in range(current_index + 1, min(len(lines), current_index + 3)):
            if i < len(lines) and lines[i].strip():
                next_line = lines[i].strip()
                # Content indicators: longer lines, starts with common content words, ends with punctuation
                return (len(next_line) > 50 or 
                       next_line.endswith(('.', '!', '?', ':', ';')) or
                       any(next_line.startswith(word) for word in ['În ', 'De ', 'Cu ', 'Pentru ', 'Prin ', 'Acest', 'Potrivit', 'După']))
        return False

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
        """Process a single HTML file using the selected extraction method"""
        # Check if already processed
        file_key = f"{domain}:{file_path}"
        if file_key in self.processed_status and self.processed_status[file_key]['status'] == 'success':
            self.stats['already_processed'] += 1
            return
        
        try:
            # Read HTML content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_html_content = f.read()
            
            # Clean HTML for better extraction
            cleaned_html_content = self.clean_html_for_extraction(original_html_content)
            
            # Save cleaned HTML if requested
            if self.save_cleaned_html:
                rel_path = os.path.relpath(file_path, CONTENT_DIR)
                cleaned_path = rel_path.replace('/raw/', '/cleaned/')
                full_cleaned_path = os.path.join(CONTENT_DIR, cleaned_path)
                
                # Create cleaned directory
                os.makedirs(os.path.dirname(full_cleaned_path), exist_ok=True)
                
                # Save cleaned HTML
                with open(full_cleaned_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_html_content)
                
                print(f"💧 Cleaned HTML saved: {full_cleaned_path}")
            
            # Reconstruct original URL
            original_url = self.reconstruct_url(domain, file_path)
            
            # Extract content using the selected method with cleaned HTML
            if self.extraction_method == 'trafilatura':
                extracted_text, extracted_metadata = self.extract_with_trafilatura(cleaned_html_content, original_url)
            elif self.extraction_method == 'newspaper':
                extracted_text, extracted_metadata = self.extract_with_newspaper(cleaned_html_content, original_url)
            else:
                raise ValueError(f"Unknown extraction method: {self.extraction_method}")
            
            if not extracted_text or len(extracted_text.strip()) < 100:
                # Skip if content is too short or extraction failed
                self.stats['skipped_files'] += 1
                self.processed_status[file_key] = {
                    'status': 'skipped',
                    'reason': f'{self.extraction_method.capitalize()} extraction failed or content too short',
                    'processed_at': datetime.now().isoformat()
                }
                return
            
            # Format headers in the extracted text
            raw_content = extracted_text.strip()
            markdown_content = self.format_headers_markdown(raw_content, cleaned_html_content)
            
            # Create basic metadata from extraction results
            metadata = {
                'title': '',
                'author': '',
                'date': '',
                'url': original_url
            }
            
            # Enhance with extracted metadata if available
            if extracted_metadata:
                if extracted_metadata.title:
                    metadata['title'] = extracted_metadata.title
                if extracted_metadata.author:
                    metadata['author'] = extracted_metadata.author
                if extracted_metadata.date:
                    metadata['date'] = extracted_metadata.date
            
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
            
            # Save metadata
            metadata.update({
                'extracted_at': datetime.now().isoformat(),
                'source_file': file_path,
                'markdown_file': full_extracted_path,
                'content_length': len(markdown_content),
                'extraction_method': self.extraction_method,
                'cleaned_html_saved': self.save_cleaned_html
            })
            
            if self.save_cleaned_html:
                metadata['cleaned_html_file'] = full_cleaned_path
            
            with open(full_metadata_path, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
            
            # Update status
            status_entry = {
                'status': 'success',
                'markdown_file': full_extracted_path,
                'metadata_file': full_metadata_path,
                'content_length': len(markdown_content),
                'extraction_method': self.extraction_method,
                'processed_at': datetime.now().isoformat()
            }
            
            if self.save_cleaned_html:
                status_entry['cleaned_html_file'] = full_cleaned_path
            
            self.processed_status[file_key] = status_entry
            
            self.stats['successful_extractions'] += 1
            print(f"✓ Extracted ({self.extraction_method}): {original_url} -> {full_extracted_path}")
                
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

    def run(self, limit=None):
        """Main processing function with optional limit"""
        start_time = time.time()
        print(f"Text Extractor started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if limit:
            print(f"Processing limit: {limit} HTML files")
        
        # Find all HTML files to process
        html_files = self.find_html_files()
        if not html_files:
            print("No HTML files found to process")
            return
        
        print(f"Found {len(html_files)} HTML files to process")
        
        # Process each file with limit
        actually_processed_count = 0
        for file_path, domain in html_files:
            # Check if file is already processed before counting towards limit
            file_key = f"{domain}:{file_path}"
            if file_key in self.processed_status and self.processed_status[file_key]['status'] == 'success':
                # This file is already processed, don't count towards limit
                print(f"Skipping already processed: {file_path}")
                self.process_html_file(file_path, domain)  # Still call to update stats
                continue
            
            if limit and actually_processed_count >= limit:
                print(f"Reached limit of {limit} HTML files")
                break
                
            print(f"Processing: {file_path}")
            self.process_html_file(file_path, domain)
            actually_processed_count += 1
        
        # Save status and print summary
        self.save_status()
        
        elapsed = time.time() - start_time
        print(f"\n=== Text Extractor Summary ===")
        print(f"Total files processed: {self.stats['total_processed']}")
        print(f"Successful extractions: {self.stats['successful_extractions']}")
        print(f"Failed extractions: {self.stats['failed_extractions']}")
        print(f"Already processed: {self.stats['already_processed']}")
        print(f"Skipped files: {self.stats['skipped_files']}")
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
    import sys
    import time
    
    # Parse command line arguments
    limit = None
    extraction_method = 'newspaper'  # Default
    save_cleaned_html = False  # Default
    
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            if limit <= 0:
                print("Error: Limit must be a positive integer")
                sys.exit(1)
        except ValueError:
            print("Error: Invalid limit value. Must be an integer.")
            sys.exit(1)
    
    # Check for extraction method argument
    if len(sys.argv) > 2:
        extraction_method = sys.argv[2].lower()
        if extraction_method not in ['trafilatura', 'newspaper']:
            print("Error: Extraction method must be 'trafilatura' or 'newspaper'")
            print("Usage: python text_extractor.py [limit] [extraction_method] [--save-cleaned-html]")
            sys.exit(1)
    
    # Check for save cleaned HTML flag
    if len(sys.argv) > 3 and sys.argv[3] == '--save-cleaned-html':
        save_cleaned_html = True
        print("💧 Cleaned HTML will be saved alongside extraction results")
    
    print(f"Using extraction method: {extraction_method}")
    extractor = TextExtractor(extraction_method=extraction_method, save_cleaned_html=save_cleaned_html)
    extractor.run(limit)